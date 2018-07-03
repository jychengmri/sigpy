import unittest
import numpy as np
import sigpy as sp
import numpy.testing as npt

from sigpy.mri import app, sim

if __name__ == '__main__':
    unittest.main()


class TestApp(unittest.TestCase):

    def shepp_logan_setup(self):
        img_shape = [6, 6]
        mps_shape = [4, 6, 6]

        img = sim.shepp_logan(img_shape)
        mps = sim.birdcage_maps(mps_shape)

        mask = np.zeros(img_shape)
        mask[:, ::2] = 1

        ksp = mask * sp.fft.fft(mps * img, axes=[-2, -1])
        return img, mps, ksp

    def test_shepp_logan_SenseRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        lamda = 0

        img_rec = app.SenseRecon(ksp, mps, lamda, alg_name='ConjugateGradient').run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

        img_rec = app.SenseRecon(ksp, mps, lamda, alg_name='GradientMethod').run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

        img_rec = app.SenseRecon(ksp, mps, lamda, alg_name='PrimalDualHybridGradient').run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_shepp_logan_SenseConstrainedRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        std = 0

        img_rec = app.SenseConstrainedRecon(ksp, mps, std).run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_shepp_logan_WaveletRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        lamda = 0

        img_rec = app.WaveletRecon(ksp, mps, lamda, alg_name='GradientMethod').run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

        img_rec = app.WaveletRecon(ksp, mps, lamda, alg_name='PrimalDualHybridGradient',
                                   max_iter=100).run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_shepp_logan_WaveletConstrainedRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        std = 0

        img_rec = app.WaveletConstrainedRecon(ksp, mps, std).run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_shepp_logan_TotalVariationRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        lamda = 0
        img_rec = app.TotalVariationRecon(ksp, mps, lamda).run()

        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_shepp_logan_TotalVariationConstrainedRecon(self):
        img, mps, ksp = self.shepp_logan_setup()
        std = 0

        img_rec = app.TotalVariationConstrainedRecon(ksp, mps, std).run()
        npt.assert_allclose(img, img_rec, atol=1e-1, rtol=1e-1)

    def test_ones_JsenseRecon(self):
        img_shape = [6, 6]
        mps_shape = [4, 6, 6]

        img = np.ones(img_shape, dtype=np.complex)
        mps = sim.birdcage_maps(mps_shape)
        ksp = sp.fft.fft(mps * img, axes=[-2, -1])

        _app = app.JsenseRecon(ksp, mps_ker_width=6, ksp_calib_width=6)
        mps_rec = _app.run()

        npt.assert_allclose(mps, mps_rec.asarray(), atol=1e-1, rtol=1e-1)