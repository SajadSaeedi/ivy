"""
Collection of MXNet general functions, wrapped to fit Ivy syntax and signature.
"""

# global
import mxnet as _mx
import numpy as _np
_round = round
import logging


def _raise(ex):
    raise ex


def _mxnet_init_context(dev):
    if dev is None or dev.find("cpu") != -1:
        mx_dev = "cpu"
    elif dev.find("cuda") != -1:
        mx_dev = "gpu"
    else:
        raise Exception("dev type not supported.")
    if dev.find(":") != -1:
        mx_dev_id = int(dev[dev.find(":")+1:])
    else:
        mx_dev_id = 0
    return _mx.Context(mx_dev, mx_dev_id)


def array(object_in, dtype_str=None, dev=None):
    cont = _mxnet_init_context('cpu' if not dev else dev)
    return _mx.nd.array(object_in, cont, dtype=dtype_str)


to_numpy = lambda x: x.asnumpy()
to_list = lambda x: x.asnumpy().tolist()
shape = lambda x: x.shape
get_num_dims = lambda x: len(x.shape)
minimum = _mx.nd.minimum
maximum = _mx.nd.maximum
clip = _mx.nd.clip
round = _mx.nd.round
floormod = lambda x, y: x % y
floor = _mx.nd.floor
ceil = _mx.nd.ceil
# noinspection PyShadowingBuiltins
abs = _mx.nd.abs
argmax = lambda x, axis=0: _mx.nd.argmax(x, axis)
argmin = lambda x, axis=0: _mx.nd.argmin(x, axis)
cast = lambda x, dtype_str: x.astype(dtype_str)


def arange(stop, start=0, step=1, dtype_str=None, dev=None):
    cont = _mxnet_init_context('cpu' if not dev else dev)
    return _mx.nd.arange(start, stop, ctx=cont, step=step, dtype=dtype_str)


def _linspace(start, stop, num):
    if num == 1:
        return start
    start = _mx.nd.array(start).reshape((1,)).astype('float32')
    stop = _mx.nd.array(stop).reshape((1,)).astype('float32')
    n_m_1 = _mx.nd.array(num - 1).reshape((1,)).astype('float32')
    increment = (stop - start)/n_m_1
    increment_tiled = _mx.nd.tile(increment, num - 1)
    increments = increment_tiled * _mx.nd.array(_mx.nd.np.linspace(1, num - 1, num - 1).tolist())
    ret = _mx.nd.concat(start, start + increments, dim=0)
    return ret


def linspace(start, stop, num, axis=None, _=None):
    num = num.asnumpy()[0] if isinstance(num, _mx.nd.NDArray) else num
    start_is_array = isinstance(start, _mx.nd.NDArray)
    stop_is_array = isinstance(stop, _mx.nd.NDArray)
    if start_is_array:
        batch_shape = list(start.shape[:-1])
        start = start.reshape((-1,))
    if stop_is_array:
        batch_shape = list(stop.shape[:-1])
        stop = stop.reshape((-1,))
    if start_is_array and stop_is_array:
        res = [_linspace(strt, stp, num) for strt, stp in zip(start, stop)]
    elif start_is_array and not stop_is_array:
        res = [_linspace(strt, stop, num) for strt in start]
    elif not start_is_array and stop_is_array:
        res = [_linspace(start, stp, num) for stp in stop]
    else:
        return _linspace(start, stop, num)
    new_shape = batch_shape + [-1, num]
    res = _mx.nd.concat(*res, dim=-1).reshape(new_shape)
    if axis is not None:
        res = _mx.nd.swapaxes(res, axis, -1)
    return res


def concatenate(xs, axis=None):
    if axis is None:
        xs = [_mx.nd.reshape(a, (-1,)) for a in xs]
        axis = 0
    return _mx.nd.concat(*xs, dim=axis)


def flip(x, axis=None, batch_shape=None):
    num_dims = len(batch_shape) if batch_shape is not None else len(x.shape)
    if axis is None:
        new_axis = list(range(num_dims))
    else:
        new_axis = axis
    if type(new_axis) is int:
        new_axis = [new_axis]
    else:
        new_axis = new_axis
    new_axis = [item + num_dims if item < 0 else item for item in new_axis]
    return _mx.nd.flip(x, new_axis)


stack = lambda xs, axis=0: _mx.nd.stack(*xs, axis=axis)


def unstack(x, axis, num_outputs=None):
    num_outputs = x.shape[axis] if not num_outputs else num_outputs
    return _mx.nd.split(x, num_outputs, axis)


def split(x, num_sections=None, axis=0):
    num_sections = x.shape[axis] if not num_sections else num_sections
    return _mx.nd.split(x, x.shape[axis] if not num_sections else num_sections, axis)


tile = _mx.nd.tile


def zero_pad(x, pad_width, x_shape=None):
    x_shape = list(x.shape) if not x_shape else x_shape
    num_dims = len(x_shape)
    if num_dims > 3:
        raise Exception('Invalid inputs. Pad for mxnet only supports inputs with 3 dimensions or smaller.')
    num_dims_to_add = 4 - num_dims
    new_shape = tuple([1] * num_dims_to_add + x_shape)
    mat_expanded_dims = _mx.nd.reshape(x, new_shape)
    pad_width_flat = [0]*num_dims_to_add*2 + [item for sublist in pad_width for item in sublist]
    pad_expanded_dims = _mx.nd.pad(mat_expanded_dims, mode="constant", pad_width=tuple(pad_width_flat))
    new_shape = [orig_dim + pad_width_item[0] + pad_width_item[1] for orig_dim, pad_width_item in zip(x_shape, pad_width)]
    res = _mx.nd.reshape(pad_expanded_dims, tuple(new_shape))
    return res


swapaxes = _mx.nd.swapaxes


def transpose(x, axes=None):
    if axes is None:
        num_dims = len(x.shape)
        axes = list(range(num_dims))
        axes.reverse()
    return _mx.nd.transpose(x, axes)


expand_dims = _mx.nd.expand_dims


def where(condition, x1, x2, _=None, _1=None):
    x_shape = list(x1.shape)
    condition_shape = list(condition.shape)
    if x_shape == condition_shape:
        return _mx.nd.where(condition, x1, x2)
    tile_reps = [int(x / c) for x, c in zip(x_shape, condition_shape)]
    tiled_condition = _mx.nd.tile(condition, tile_reps)
    return _mx.nd.where(tiled_condition, x1, x2)


def indices_where(x):
    x_shape = x.shape
    x_flat = x.reshape((1, -1,))
    flat_indices = x_flat.astype('int32').tostype('csr').indices
    if flat_indices.shape == (0,):
        res = flat_indices.reshape((0, len(x_shape)))
        return res
    res = _mx.nd.swapaxes(_mx.nd.unravel_index(flat_indices, x_shape), 0, 1)
    return res


reshape = lambda x, new_shape: x.reshape(new_shape)
squeeze = lambda x, axis=None: _mx.nd.squeeze(x, axis)


# noinspection PyShadowingNames
def zeros(shape, dtype_str='float32', dev=None):
    cont = _mxnet_init_context('cpu' if not dev else dev)
    return _mx.nd.zeros(shape, ctx=cont).astype(dtype_str)


def zeros_like(x, dtype_str=None, dev=None):
    mx_zeros = _mx.nd.zeros_like(x, ctx=_mxnet_init_context('cpu' if not dev else dev))
    return mx_zeros if not dtype_str else mx_zeros.astype(dtype_str)


# noinspection PyShadowingNames
def ones(shape, dtype_str='float32', dev=None):
    cont = _mxnet_init_context('cpu' if not dev else dev)
    return _mx.nd.ones(shape, ctx=cont).astype(dtype_str)


def ones_like(x, dtype_str=None, dev=None):
    mx_ones = _mx.nd.ones_like(x, ctx=_mxnet_init_context('cpu' if not dev else dev))
    return mx_ones if dtype_str is None else mx_ones.astype(dtype_str)


# noinspection PyUnusedLocal
one_hot = lambda indices, depth, dev=None: _mx.nd.one_hot(indices, depth)


def cross(x1, x2):
    a1 = x1[..., 0:1]
    a2 = x1[..., 1:2]
    a3 = x1[..., 2:3]
    b1 = x2[..., 0:1]
    b2 = x2[..., 1:2]
    b3 = x2[..., 2:3]
    res1 = a2*b3 - a3*b2
    res2 = a3*b1 - a1*b3
    res3 = a1*b2 - a2*b1
    res = _mx.nd.concat(res1, res2, res3, dim=-1)
    return res


def matmul(x1, x2, batch_shape=None):
    expand = len(batch_shape) == 0 if batch_shape is not None else len(x1.shape) < 3
    if expand:
        x1 = _mx.nd.expand_dims(x1, 0)
        x2 = _mx.nd.expand_dims(x2, 0)
    res = _mx.nd.batch_dot(x1, x2)
    return res[0] if expand else res


cumsum = lambda x, axis=0: _mx.nd.cumsum(x, axis)


def identity(n, dtype_str='float32', batch_shape=None, dev=None):
    mat = _mx.nd.eye(n, dtype=dtype_str).copyto(_mxnet_init_context('cpu' if not dev else dev))
    if batch_shape is None:
        return mat
    else:
        reshape_dims = [1]*len(batch_shape) + [n, n]
        tile_dims = list(batch_shape) + [1, 1]
        res = _mx.nd.tile(_mx.nd.reshape(mat, reshape_dims), tile_dims)
        return res


# noinspection PyShadowingNames
def scatter_flat(indices, updates, size, reduction='sum', dev=None):
    if reduction == 'sum':
        return _mx.nd.scatter_nd(updates, _mx.nd.expand_dims(indices, 0), [size]).copyto(_mxnet_init_context('cpu' if not dev else dev))
    else:
        raise Exception('MXNet scatter_nd currently only supports reduction mode "sum", but {} selected.'.
                        format(reduction))


# noinspection PyShadowingNames
def scatter_nd(indices, updates, shape, num_idx_dims=None, reduction='sum', dev=None):
    shape = list(shape)
    num_idx_dims = len(indices.shape) if num_idx_dims is None else num_idx_dims
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    shape = shape if type(shape) is list else shape.asnumpy().astype(_np.int32).tolist()
    if reduction == 'sum':
        return _mx.nd.scatter_nd(updates, indices, shape).copyto(_mxnet_init_context('cpu' if not dev else dev))
    else:
        raise Exception('MXNet scatter_nd currently only supports reduction mode "sum", but {} selected.'.
                        format(reduction))


def gather_flat(params, indices, dev=None):
    if dev is None:
        dev = get_device(params)
    return _mx.nd.gather_nd(params, _mx.nd.expand_dims(indices, 0)).copyto(_mxnet_init_context('cpu' if not dev else dev))


def gather_nd(params, indices, indices_shape=None, dev=None):
    if dev is None:
        dev = get_device(params)
    if indices_shape is None:
        indices_shape = indices.shape
    num_idx_dims = len(indices_shape)
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    return _mx.nd.gather_nd(params, indices).copyto(_mxnet_init_context('cpu' if not dev else dev))


get_device = lambda x: x.context.device_type
dtype = lambda x: x.dtype


# noinspection PyUnusedLocal
def compile_fn(func, example_inputs=None):
    logging.warning('MXnet does not support compiling arbitrary functions, '
                    'consider writing a function using MXNet Symbolic backend instead for compiling.\n'
                    'Now returning the unmodified function.')
    return func
