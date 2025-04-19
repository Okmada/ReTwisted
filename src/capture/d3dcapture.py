import ctypes

import numpy as np

import rotypes.roapi
import rotypes.Windows.Graphics.Capture
import rotypes.Windows.Graphics.DirectX
from rotypes.inspectable import IInspectable
from rotypes.Windows.Foundation import TypedEventHandler
from rotypes.Windows.Graphics.DirectX.Direct3D11 import (
    CreateDirect3D11DeviceFromDXGIDevice, IDirect3DDevice,
    IDirect3DDxgiInterfaceAccess)

from . import d3d11

PBYTE = ctypes.POINTER(ctypes.c_ubyte)

class CaptureSession:
    def __init__(self):
        self._rtdevice = IDirect3DDevice()
        self._dxdevice = d3d11.ID3D11Device()
        self._immediatedc = d3d11.ID3D11DeviceContext()
        self._framepool = None
        self._session = None
        self._item = None
        self._last_size = None
        self.frame_callback = None
        self.close_callback = None
        self.cputex = None

    def _create_device(self):
        d3d11.D3D11CreateDevice(
            None,
            d3d11.D3D_DRIVER_TYPE_HARDWARE,
            None,
            d3d11.D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            None,
            0,
            d3d11.D3D11_SDK_VERSION,
            ctypes.byref(self._dxdevice),
            None,
            ctypes.byref(self._immediatedc)
        )
        self._rtdevice = CreateDirect3D11DeviceFromDXGIDevice(self._dxdevice)
        self._evtoken = None

    def start(self, hwnd, capture_cursor=False):
        self.stop()
        self._create_device()
        interop = rotypes.roapi.GetActivationFactory('Windows.Graphics.Capture.GraphicsCaptureItem').astype(rotypes.Windows.Graphics.Capture.IGraphicsCaptureItemInterop)
        item = interop.CreateForWindow(hwnd, rotypes.Windows.Graphics.Capture.IGraphicsCaptureItem.GUID)
        self._item = item
        self._last_size = item.Size
        self._reset_cputex(item.Size)
        delegate = TypedEventHandler(rotypes.Windows.Graphics.Capture.GraphicsCaptureItem, IInspectable).delegate(self._closed_callback)
        self._evtoken = item.add_Closed(delegate)
        self._framepool = rotypes.Windows.Graphics.Capture.Direct3D11CaptureFramePool.CreateFreeThreaded(self._rtdevice, rotypes.Windows.Graphics.DirectX.DirectXPixelFormat.B8G8R8A8UIntNormalized, 1, item.Size)
        self._session = self._framepool.CreateCaptureSession(item)
        pool = self._framepool
        pool.add_FrameArrived(TypedEventHandler(rotypes.Windows.Graphics.Capture.Direct3D11CaptureFramePool, IInspectable).delegate(self._frame_arrived_callback))
        # self._session.IsBorderRequired = False
        self._session.IsCursorCaptureEnabled = capture_cursor
        self._session.StartCapture()

    def _frame_arrived_callback(self, x, y):
        if self.frame_callback is not None:
            self.frame_callback(self)

    def _closed_callback(self, x, y):
        self.stop()
        if self.close_callback is not None:
            self.close_callback(self)

    def stop(self):
        if self._framepool is not None:
            self._framepool.Close()
            self._framepool = None
        if self._session is not None:
            # self._session.Close()  # E_UNEXPECTED ???
            self._session = None
        self._item = None
        self._rtdevice.Release()
        self._dxdevice.Release()
        if self.cputex:
            self.cputex.Release()

    def _reset_cputex(self, size):
        if self.cputex is not None:
            self.cputex.Release()
        desc2 = d3d11.D3D11_TEXTURE2D_DESC()
        desc2.Width = size.Width
        desc2.Height = size.Height
        desc2.MipLevels = 1
        desc2.ArraySize = 1
        desc2.Format = d3d11.DXGI_FORMAT_B8G8R8A8_UNORM
        desc2.SampleDesc = d3d11.DXGI_SAMPLE_DESC(Count=1, Quality=0)
        desc2.Usage = d3d11.D3D11_USAGE_STAGING
        desc2.CPUAccessFlags = d3d11.D3D11_CPU_ACCESS_READ
        desc2.BindFlags = 0
        desc2.MiscFlags = 0
        self.cputex_desc = desc2
        self.cputex = self._dxdevice.CreateTexture2D(ctypes.byref(desc2), None)

    def _reset_framepool(self, size, reset_device=False):
        if reset_device:
            self._create_device()
        self._framepool.Recreate(self._rtdevice, rotypes.Windows.Graphics.DirectX.DirectXPixelFormat.B8G8R8A8UIntNormalized, 1, size)
        self._reset_cputex(size)

    def get_frame(self):
        frame = self._framepool.TryGetNextFrame()
        if not frame:
            return None
        img = None
        with frame:
            need_reset_framepool = False
            need_reset_device = False
            if frame.ContentSize.Width != self._last_size.Width or frame.ContentSize.Height != self._last_size.Height:
                # print('size changed')
                need_reset_framepool = True
                self._last_size = frame.ContentSize
            
            if need_reset_framepool:
                self._reset_framepool(frame.ContentSize)
                return self.get_frame()
            tex = None
            try:
                tex = frame.Surface.astype(IDirect3DDxgiInterfaceAccess).GetInterface(d3d11.ID3D11Texture2D.GUID).astype(d3d11.ID3D11Texture2D)
                # desc = tex.GetDesc()
                desc = self.cputex_desc
                self._immediatedc.CopyResource(self.cputex, tex)
                mapinfo = self._immediatedc.Map(self.cputex, 0, d3d11.D3D11_MAP_READ, 0)
                mat = np.ctypeslib.as_array(ctypes.cast(mapinfo.pData, PBYTE), (desc.Height, mapinfo.RowPitch // 4, 4))[:, :desc.Width].copy()
                img = mat[:,:,:3]
                self._immediatedc.Unmap(self.cputex, 0)
            except OSError as e:
                if e.winerror == d3d11.DXGI_ERROR_DEVICE_REMOVED or e.winerror == d3d11.DXGI_ERROR_DEVICE_RESET:
                    need_reset_framepool = True
                    need_reset_device = True
                else:
                    raise
            finally:
                if tex is not None:
                    tex.Release()
            if need_reset_framepool:
                    self._reset_framepool(frame.ContentSize, need_reset_device)
                    return self.get_frame()
        return img
