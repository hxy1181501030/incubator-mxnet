# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import print_function
import mxnet as mx
from mxnet.gluon import contrib
from mxnet.gluon import nn
from mxnet.gluon.contrib.nn import (
    Concurrent, HybridConcurrent, Identity, SparseEmbedding, PixelShuffle1D,
    PixelShuffle2D, PixelShuffle3D)
from mxnet.test_utils import almost_equal
from common import setup_module, with_seed, teardown
import numpy as np
from numpy.testing import assert_allclose


def check_rnn_cell(cell, prefix, in_shape=(10, 50), out_shape=(10, 100), begin_state=None):
    inputs = [mx.sym.Variable('rnn_t%d_data'%i) for i in range(3)]
    outputs, _ = cell.unroll(3, inputs, begin_state=begin_state)
    outputs = mx.sym.Group(outputs)
    assert sorted(cell.collect_params().keys()) == [prefix+'h2h_bias', prefix+'h2h_weight',
                                                    prefix+'i2h_bias', prefix+'i2h_weight']
    assert outputs.list_outputs() == [prefix+'t0_out_output', prefix+'t1_out_output', prefix+'t2_out_output']

    args, outs, auxs = outputs.infer_shape(rnn_t0_data=in_shape,
                                           rnn_t1_data=in_shape,
                                           rnn_t2_data=in_shape)
    assert outs == [out_shape]*3


def check_rnn_forward(layer, inputs):
    inputs.attach_grad()
    layer.collect_params().initialize()
    with mx.autograd.record():
        layer.unroll(3, inputs, merge_outputs=True)[0].backward()
        mx.autograd.backward(layer.unroll(3, inputs, merge_outputs=False)[0])
    mx.nd.waitall()


@with_seed()
def test_rnn_cells():
    check_rnn_forward(contrib.rnn.Conv1DLSTMCell((5, 7), 10, (3,), (3,)),
                      mx.nd.ones((8, 3, 5, 7)))
    check_rnn_forward(contrib.rnn.Conv1DRNNCell((5, 7), 10, (3,), (3,)),
                      mx.nd.ones((8, 3, 5, 7)))
    check_rnn_forward(contrib.rnn.Conv1DGRUCell((5, 7), 10, (3,), (3,)),
                      mx.nd.ones((8, 3, 5, 7)))

    net = mx.gluon.rnn.SequentialRNNCell()
    net.add(contrib.rnn.Conv1DLSTMCell((5, 7), 10, (3,), (3,)))
    net.add(contrib.rnn.Conv1DRNNCell((10, 5), 11, (3,), (3,)))
    net.add(contrib.rnn.Conv1DGRUCell((11, 3), 12, (3,), (3,)))
    check_rnn_forward(net, mx.nd.ones((8, 3, 5, 7)))


@with_seed()
def test_convrnn():
    cell = contrib.rnn.Conv1DRNNCell((10, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 50), out_shape=(1, 100, 48))

    cell = contrib.rnn.Conv2DRNNCell((10, 20, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 50), out_shape=(1, 100, 18, 48))

    cell = contrib.rnn.Conv3DRNNCell((10, 20, 30, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 30, 50), out_shape=(1, 100, 18, 28, 48))


@with_seed()
def test_convlstm():
    cell = contrib.rnn.Conv1DLSTMCell((10, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 50), out_shape=(1, 100, 48))

    cell = contrib.rnn.Conv2DLSTMCell((10, 20, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 50), out_shape=(1, 100, 18, 48))

    cell = contrib.rnn.Conv3DLSTMCell((10, 20, 30, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 30, 50), out_shape=(1, 100, 18, 28, 48))


@with_seed()
def test_convgru():
    cell = contrib.rnn.Conv1DGRUCell((10, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 50), out_shape=(1, 100, 48))

    cell = contrib.rnn.Conv2DGRUCell((10, 20, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 50), out_shape=(1, 100, 18, 48))

    cell = contrib.rnn.Conv3DGRUCell((10, 20, 30, 50), 100, 3, 3, prefix='rnn_')
    check_rnn_cell(cell, prefix='rnn_', in_shape=(1, 10, 20, 30, 50), out_shape=(1, 100, 18, 28, 48))


@with_seed()
def test_conv_fill_shape():
    cell = contrib.rnn.Conv1DLSTMCell((0, 7), 10, (3,), (3,))
    cell.hybridize()
    check_rnn_forward(cell, mx.nd.ones((8, 3, 5, 7)))
    assert cell.i2h_weight.shape[1] == 5, cell.i2h_weight.shape[1]

@with_seed()
def test_lstmp():
    nhid = 100
    nproj = 64
    cell = contrib.rnn.LSTMPCell(nhid, nproj, prefix='rnn_')
    inputs = [mx.sym.Variable('rnn_t%d_data'%i) for i in range(3)]
    outputs, _ = cell.unroll(3, inputs)
    outputs = mx.sym.Group(outputs)
    expected_params = ['rnn_h2h_bias', 'rnn_h2h_weight', 'rnn_h2r_weight', 'rnn_i2h_bias', 'rnn_i2h_weight']
    expected_outputs = ['rnn_t0_out_output', 'rnn_t1_out_output', 'rnn_t2_out_output']
    assert sorted(cell.collect_params().keys()) == expected_params
    assert outputs.list_outputs() == expected_outputs, outputs.list_outputs()

    args, outs, auxs = outputs.infer_shape(rnn_t0_data=(10,50), rnn_t1_data=(10,50), rnn_t2_data=(10,50))
    assert outs == [(10, nproj), (10, nproj), (10, nproj)]


@with_seed()
def test_vardrop():
    def check_vardrop(drop_inputs, drop_states, drop_outputs):
        cell = contrib.rnn.VariationalDropoutCell(mx.gluon.rnn.RNNCell(100, prefix='rnn_'),
                                                  drop_outputs=drop_outputs,
                                                  drop_states=drop_states,
                                                  drop_inputs=drop_inputs)
        cell.collect_params().initialize(init='xavier')
        input_data = mx.nd.random_uniform(shape=(10, 3, 50), ctx=mx.context.current_context())
        with mx.autograd.record():
            outputs1, _ = cell.unroll(3, input_data, merge_outputs=True)
            mx.nd.waitall()
            outputs2, _ = cell.unroll(3, input_data, merge_outputs=True)
        assert not almost_equal(outputs1.asnumpy(), outputs2.asnumpy())

        inputs = [mx.sym.Variable('rnn_t%d_data'%i) for i in range(3)]
        outputs, _ = cell.unroll(3, inputs, merge_outputs=False)
        outputs = mx.sym.Group(outputs)

        args, outs, auxs = outputs.infer_shape(rnn_t0_data=(10,50), rnn_t1_data=(10,50), rnn_t2_data=(10,50))
        assert outs == [(10, 100), (10, 100), (10, 100)]

        cell.reset()
        cell.hybridize()
        with mx.autograd.record():
            outputs3, _ = cell.unroll(3, input_data, merge_outputs=True)
            mx.nd.waitall()
            outputs4, _ = cell.unroll(3, input_data, merge_outputs=True)
        assert not almost_equal(outputs3.asnumpy(), outputs4.asnumpy())
        assert not almost_equal(outputs1.asnumpy(), outputs3.asnumpy())

    check_vardrop(0.5, 0.5, 0.5)
    check_vardrop(0.5, 0, 0.5)


def test_concurrent():
    model = HybridConcurrent(axis=1)
    model.add(nn.Dense(128, activation='tanh', in_units=10))
    model.add(nn.Dense(64, activation='tanh', in_units=10))
    model.add(nn.Dense(32, in_units=10))
    model2 = Concurrent(axis=1)
    model2.add(nn.Dense(128, activation='tanh', in_units=10))
    model2.add(nn.Dense(64, activation='tanh', in_units=10))
    model2.add(nn.Dense(32, in_units=10))

    # symbol
    x = mx.sym.var('data')
    y = model(x)
    assert len(y.list_arguments()) == 7

    # ndarray
    model.initialize(mx.init.Xavier(magnitude=2.24))
    model2.initialize(mx.init.Xavier(magnitude=2.24))
    x = model(mx.nd.zeros((32, 10)))
    x2 = model2(mx.nd.zeros((32, 10)))
    assert x.shape == (32, 224)
    assert x2.shape == (32, 224)
    x.wait_to_read()
    x2.wait_to_read()

@with_seed()
def test_identity():
    model = Identity()
    x = mx.nd.random.uniform(shape=(128, 33, 64))
    mx.test_utils.assert_almost_equal(model(x).asnumpy(),
                                      x.asnumpy())

@with_seed()
def test_sparse_embedding():
    layer = SparseEmbedding(10, 100)
    layer.initialize()
    trainer = mx.gluon.Trainer(layer.collect_params(), 'sgd')
    x = mx.nd.array([3,4,2,0,1])
    with mx.autograd.record():
        y = layer(x)
        y.backward()
    assert (layer.weight.grad().asnumpy()[:5] == 1).all()
    assert (layer.weight.grad().asnumpy()[5:] == 0).all()

def test_pixelshuffle1d():
    nchan = 2
    up_x = 2
    nx = 3
    shape_before = (1, nchan * up_x, nx)
    shape_after = (1, nchan, nx * up_x)
    layer = PixelShuffle1D(up_x)
    x = mx.nd.arange(np.prod(shape_before)).reshape(shape_before)
    y = layer(x)
    assert y.shape == shape_after
    assert_allclose(
        y.asnumpy(),
        [[[0, 3, 1, 4, 2, 5],
          [6, 9, 7, 10, 8, 11]]]
    )

def test_pixelshuffle2d():
    nchan = 2
    up_x = 2
    up_y = 3
    nx = 2
    ny = 3
    shape_before = (1, nchan * up_x * up_y, nx, ny)
    shape_after = (1, nchan, nx * up_x, ny * up_y)
    layer = PixelShuffle2D((up_x, up_y))
    x = mx.nd.arange(np.prod(shape_before)).reshape(shape_before)
    y = layer(x)
    assert y.shape == shape_after
    # - Channels are reshaped to form 2x3 blocks
    # - Within each block, the increment is `nx * ny` when increasing the column
    #   index by 1
    # - Increasing the block index adds an offset of 1
    # - Increasing the channel index adds an offset of `nx * up_x * ny * up_y`
    assert_allclose(
        y.asnumpy(),
        [[[[ 0,  6, 12,  1,  7, 13,  2,  8, 14],
           [18, 24, 30, 19, 25, 31, 20, 26, 32],
           [ 3,  9, 15,  4, 10, 16,  5, 11, 17],
           [21, 27, 33, 22, 28, 34, 23, 29, 35]],

          [[36, 42, 48, 37, 43, 49, 38, 44, 50],
           [54, 60, 66, 55, 61, 67, 56, 62, 68],
           [39, 45, 51, 40, 46, 52, 41, 47, 53],
           [57, 63, 69, 58, 64, 70, 59, 65, 71]]]]
    )

def test_pixelshuffle3d():
    nchan = 1
    up_x = 2
    up_y = 1
    up_z = 2
    nx = 2
    ny = 3
    nz = 4
    shape_before = (1, nchan * up_x * up_y * up_z, nx, ny, nz)
    shape_after = (1, nchan, nx * up_x, ny * up_y, nz * up_z)
    layer = PixelShuffle3D((up_x, up_y, up_z))
    x = mx.nd.arange(np.prod(shape_before)).reshape(shape_before)
    y = layer(x)
    assert y.shape == shape_after
    # - Channels are reshaped to form 2x1x2 blocks
    # - Within each block, the increment is `nx * ny * nz` when increasing the
    #   column index by 1, e.g. the block [[[ 0, 24]], [[48, 72]]]
    # - Increasing the block index adds an offset of 1
    assert_allclose(
        y.asnumpy(),
        [[[[[ 0, 24,  1, 25,  2, 26,  3, 27],
            [ 4, 28,  5, 29,  6, 30,  7, 31],
            [ 8, 32,  9, 33, 10, 34, 11, 35]],

           [[48, 72, 49, 73, 50, 74, 51, 75],
            [52, 76, 53, 77, 54, 78, 55, 79],
            [56, 80, 57, 81, 58, 82, 59, 83]],

           [[12, 36, 13, 37, 14, 38, 15, 39],
            [16, 40, 17, 41, 18, 42, 19, 43],
            [20, 44, 21, 45, 22, 46, 23, 47]],

           [[60, 84, 61, 85, 62, 86, 63, 87],
            [64, 88, 65, 89, 66, 90, 67, 91],
            [68, 92, 69, 93, 70, 94, 71, 95]]]]]
    )

def test_datasets():
    wikitext2_train = contrib.data.text.WikiText2(root='data/wikitext-2', segment='train')
    wikitext2_val = contrib.data.text.WikiText2(root='data/wikitext-2', segment='validation',
                                                vocab=wikitext2_train.vocabulary)
    wikitext2_test = contrib.data.text.WikiText2(root='data/wikitext-2', segment='test')
    assert len(wikitext2_train) == 59305,  len(wikitext2_train)
    assert len(wikitext2_train.vocabulary) == 33278, len(wikitext2_train.vocabulary)
    assert len(wikitext2_train.frequencies) == 33277, len(wikitext2_train.frequencies)
    assert len(wikitext2_val) == 6181, len(wikitext2_val)
    assert len(wikitext2_val.vocabulary) == 33278, len(wikitext2_val.vocabulary)
    assert len(wikitext2_val.frequencies) == 13776, len(wikitext2_val.frequencies)
    assert len(wikitext2_test) == 6974, len(wikitext2_test)
    assert len(wikitext2_test.vocabulary) == 14143, len(wikitext2_test.vocabulary)
    assert len(wikitext2_test.frequencies) == 14142, len(wikitext2_test.frequencies)
    assert wikitext2_test.frequencies['English'] == 32


def test_sampler():
    interval_sampler = contrib.data.IntervalSampler(10, 3)
    assert sorted(list(interval_sampler)) == list(range(10))
    interval_sampler = contrib.data.IntervalSampler(10, 3, rollover=False)
    assert list(interval_sampler) == [0, 3, 6, 9]


if __name__ == '__main__':
    import nose
    nose.runmodule()
