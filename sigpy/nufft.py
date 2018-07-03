import numpy as np
from sigpy import fft, util, interp


def nufft(input, coord, oversamp=1.25, width=4.0, n=128):
    '''Non-uniform Fast Fourier Transform.

    Args:
        input (numpy/cupy array): input array.
        coord (numpy/cupy array): coordinate array of shape (..., ndim). 
            ndim determines the number of dimension to apply nufft.
        oversamp (float): oversampling factor.
        width (float): interpolation kernel full-width in terms of oversampled grid.
        n (int): number of sampling points of interpolation kernel.

    Returns:
        numpy/cupy array of shape input.shape[:-ndim] + coord.shape[:-1]
    '''
    device = util.get_device(input)
    xp = device.xp
    ndim = coord.shape[-1]
    beta = np.pi * (((width / oversamp) * (oversamp - 0.5))**2 - 0.8)**0.5

    with device:
        output = input.copy()
        os_shape = list(input.shape)
        
        for a in range(-ndim, 0):

            i = input.shape[a]
            os_i = util.get_ugly_number(oversamp * i)
            os_shape[a] = os_i
            idx = xp.arange(i, dtype=input.dtype)
            os_idx = xp.arange(os_i, dtype=input.dtype)

            # Calculate apodization
            apod = (beta**2 - (np.pi * width * (idx - i // 2) / os_i)**2)**0.5
            apod /= xp.sinh(apod)

            # Swap axes
            output = output.swapaxes(a, -1)
            os_shape[a], os_shape[-1] = os_shape[-1], os_shape[a]

            # Apodize
            output *= apod

            # Oversampled FFT
            mod = xp.exp(1j * 2 * np.pi * (os_idx - (os_i // 2) / 2) * ((os_i // 2) / os_i))
            output = util.resize(output, os_shape)
            output *= mod
            output = fft.fft(output, axes=[-1], center=False, norm=None)
            output *= mod / i**0.5

            # Swap back
            output = output.swapaxes(a, -1)
            os_shape[a], os_shape[-1] = os_shape[-1], os_shape[a]

        coord = _scale_coord(util.move(coord, device), input.shape, oversamp)
        table = util.move(
            kb(np.arange(n, dtype=coord.dtype) / n, width, beta, dtype=coord.dtype), device)

        output = interp.interp(output, width, table, coord)

        return output
    
def estimate_shape(coord):
    ndim = coord.shape[-1]
    with util.get_device(coord):
        shape = [int(coord[..., i].max() - coord[..., i].min()) for i in range(ndim)]

    return shape


def nufft_adjoint(input, coord, oshape=None, oversamp=1.25, width=4.0, n=128):
    '''Adjoint non-uniform Fast Fourier Transform.

    Args:
        input (numpy/cupy array): input array.
        coord (numpy/cupy array): coordinate array of shape (..., ndim). 
            ndim determines the number of dimension to apply nufft adjoint.
        oshape (tuple of ints): output shape.
        oversamp (float): oversampling factor.
        width (float): interpolation kernel full-width in terms of oversampled grid.
        n (int): number of sampling points of interpolation kernel.

    Returns:
        numpy/cupy array.
    '''
    device = util.get_device(input)
    xp = device.xp
    ndim = coord.shape[-1]
    beta = np.pi * (((width / oversamp) * (oversamp - 0.5))**2 - 0.8)**0.5
    if oshape is None:
        oshape = list(input.shape[:-coord.ndim + 1]) + estimate_shape(coord)
    else:
        oshape = list(oshape)

    with device:

        coord = _scale_coord(util.move(coord, device), oshape, oversamp)
        table = util.move(
            kb(np.arange(n, dtype=coord.dtype) / n, width, beta, dtype=coord.dtype), device)
        os_shape = oshape[:-ndim] + [util.get_ugly_number(oversamp * i) for i in oshape[-ndim:]]
        output = interp.gridding(input, os_shape, width, table, coord)

        for a in range(-ndim, 0):

            i = oshape[a]
            os_i = os_shape[a]
            idx = xp.arange(i, dtype=input.dtype)
            os_idx = xp.arange(os_i, dtype=input.dtype)
            
            os_shape[a] = i

            # Swap axes
            output = output.swapaxes(a, -1)
            os_shape[a], os_shape[-1] = os_shape[-1], os_shape[a]

            # Oversampled IFFT
            imod = xp.exp(-1j * 2 * np.pi * (os_idx - (os_i // 2) / 2) * ((os_i // 2) / os_i))

            output *= imod
            output = fft.ifft(output, axes=[-1], center=False, norm=None)
            output *= imod * os_i / i**0.5
            output = util.resize(output, os_shape)
            
            # Calculate apodization
            apod = (beta**2 - (np.pi * width * (idx - i // 2) / os_i)**2)**0.5
            apod /= xp.sinh(apod)

            # Apodize
            output *= apod

            # Swap back
            output = output.swapaxes(a, -1)
            os_shape[a], os_shape[-1] = os_shape[-1], os_shape[a]

        return output

    
def kb(x, width, beta, dtype=np.complex):
    return 1 / width * np.i0(beta * np.sqrt(1 - x**2)).astype(dtype)


def _scale_coord(coord, shape, oversamp):

    ndim = coord.shape[-1]
    device = util.get_device(coord)
    scale = util.move([util.get_ugly_number(oversamp * i) / i for i in shape[-ndim:]], device)
    shift = util.move([util.get_ugly_number(oversamp * i) // 2 for i in shape[-ndim:]], device)

    with device:
        coord = scale * coord + shift

    return coord