#include "pch.h"
#include "Rendering/ImageLoader.h"

using namespace winrt;
using namespace Windows::Graphics::Imaging;

namespace winrt::PDFEditor::Rendering
{
    ImageLoader::ImageLoader()
    {
    }

    void ImageLoader::EnsureWIC()
    {
        if (!m_wicFactory)
        {
            CoCreateInstance(CLSID_WICImagingFactory, nullptr,
                CLSCTX_INPROC_SERVER, __uuidof(IWICImagingFactory),
                m_wicFactory.put_void());
        }
    }

    bool ImageLoader::Initialize()
    {
        EnsureWIC();
        return m_wicFactory != nullptr;
    }

    void ImageLoader::Shutdown()
    {
        m_pixelData.clear();
        m_bitmap = nullptr;
        m_frame = nullptr;
        m_decoder = nullptr;
        m_scaler = nullptr;
        m_wicFactory = nullptr;
        m_width = 0;
        m_height = 0;
    }

    bool ImageLoader::LoadFromFile(hstring const& filePath)
    {
        EnsureWIC();
        if (!m_wicFactory) return false;

        auto path = std::wstring(filePath);

        HRESULT hr = m_wicFactory->CreateDecoderFromFilename(
            path.c_str(), nullptr, GENERIC_READ,
            WICDecodeMetadataCacheOnLoad, m_decoder.put());

        if (FAILED(hr))
        {
            OutputDebugStringW(L"[ImageLoader] Failed to load: ");
            OutputDebugStringW(path.c_str());
            OutputDebugStringW(L"\n");
            return false;
        }

        hr = m_decoder->GetFrame(0, m_frame.put());
        if (FAILED(hr)) return false;

        return CreateBitmapFromFrame();
    }

    bool ImageLoader::LoadFromMemory(const uint8_t* data, uint32_t dataSize)
    {
        EnsureWIC();
        if (!m_wicFactory || !data) return false;

        IStream* stream = nullptr;
        CreateStreamOnHGlobal(nullptr, TRUE, &stream);
        stream->Write(data, dataSize, nullptr);
        stream->Seek({ 0 }, STREAM_SEEK_SET, nullptr);

        HRESULT hr = m_wicFactory->CreateDecoderFromStream(
            stream, nullptr, WICDecodeMetadataCacheOnLoad, m_decoder.put());

        stream->Release();

        if (FAILED(hr)) return false;

        hr = m_decoder->GetFrame(0, m_frame.put());
        if (FAILED(hr)) return false;

        return CreateBitmapFromFrame();
    }

    bool ImageLoader::LoadFromResource(int resourceId)
    {
        auto hModule = GetModuleHandleW(nullptr);
        auto hResource = FindResourceW(hModule, MAKEINTRESOURCEW(resourceId), L"IMAGE");
        if (!hResource) return false;

        auto hData = LoadResource(hModule, hResource);
        if (!hData) return false;

        auto size = SizeofResource(hModule, hResource);
        auto data = static_cast<const uint8_t*>(LockResource(hData));

        return LoadFromMemory(data, static_cast<uint32_t>(size));
    }

    bool ImageLoader::CreateBitmapFromFrame()
    {
        if (!m_frame || !m_wicFactory) return false;

        m_frame->GetSize(&m_width, &m_height);

        HRESULT hr = m_wicFactory->CreateBitmapFromSource(
            m_frame.get(), WICBitmapCacheOnDemand, m_bitmap.put());

        if (FAILED(hr)) return false;

        m_pixelData.resize(m_width * m_height * 4);

        WICRect rect = { 0, 0, static_cast<INT>(m_width), static_cast<INT>(m_height) };
        hr = m_bitmap->CopyPixels(&rect, m_width * 4,
            static_cast<UINT32>(m_pixelData.size()), m_pixelData.data());

        return SUCCEEDED(hr);
    }

    uint32_t ImageLoader::GetWidth() const { return m_width; }
    uint32_t ImageLoader::GetHeight() const { return m_height; }
    void* ImageLoader::GetPixelData() const
    {
        return const_cast<uint8_t*>(m_pixelData.data());
    }

    BitmapPixelFormat ImageLoader::GetPixelFormat() const { return m_pixelFormat; }

    bool ImageLoader::SaveToFile(hstring const& filePath)
    {
        EnsureWIC();
        if (!m_wicFactory || !m_bitmap) return false;

        winrt::com_ptr<IWICBitmapEncoder> encoder;
        auto path = std::wstring(filePath);

        GUID containerFormat = GUID_ContainerFormatPng;
        if (path.ends_with(L".jpg") || path.ends_with(L".jpeg"))
            containerFormat = GUID_ContainerFormatJpeg;
        else if (path.ends_with(L".bmp"))
            containerFormat = GUID_ContainerFormatBmp;
        else if (path.ends_with(L".tiff"))
            containerFormat = GUID_ContainerFormatTiff;

        HRESULT hr = m_wicFactory->CreateEncoder(containerFormat, nullptr, encoder.put());
        if (FAILED(hr)) return false;

        winrt::com_ptr<IStream> stream;
        SHCreateStreamOnFileW(path.c_str(), STGM_WRITE, stream.put());
        hr = encoder->Initialize(stream.get(), WICBitmapEncoderNoCache);
        if (FAILED(hr)) return false;

        winrt::com_ptr<IWICBitmapFrameEncode> encodeFrame;
        IPropertyBag2* props = nullptr;
        hr = encoder->CreateNewFrame(encodeFrame.put(), &props);
        if (FAILED(hr)) return false;

        encodeFrame->Initialize(props);
        encodeFrame->SetSize(m_width, m_height);
        encodeFrame->WritePixels(m_height, m_width * 4,
            m_width * m_height * 4, m_pixelData.data());
        encodeFrame->Commit();
        encoder->Commit();

        return true;
    }

    Microsoft::UI::Xaml::Media::ImageSource ImageLoader::CreateImageSource()
    {
        if (m_pixelData.empty()) return nullptr;

        auto bitmap = Microsoft::UI::Xaml::Media::Imaging::SoftwareBitmapSource();
        return bitmap;
    }

    void ImageLoader::Resize(uint32_t newWidth, uint32_t newHeight)
    {
        if (!m_wicFactory || !m_bitmap) return;

        winrt::com_ptr<IWICBitmapScaler> scaler;
        m_wicFactory->CreateBitmapScaler(scaler.put());

        scaler->Initialize(m_bitmap.get(), newWidth, newHeight, WICBitmapInterpolationModeFant);

        m_width = newWidth;
        m_height = newHeight;
        m_bitmap = nullptr;
        scaler->QueryInterface(__uuidof(IWICBitmap), m_bitmap.put_void());

        m_pixelData.resize(m_width * m_height * 4);
        WICRect rect = { 0, 0, static_cast<INT>(m_width), static_cast<INT>(m_height) };
        m_bitmap->CopyPixels(&rect, m_width * 4,
            static_cast<UINT32>(m_pixelData.size()), m_pixelData.data());
    }

    void ImageLoader::Crop(uint32_t x, uint32_t y, uint32_t width, uint32_t height)
    {
        if (!m_wicFactory || !m_bitmap) return;

        WICRect rect = { static_cast<INT>(x), static_cast<INT>(y),
                        static_cast<INT>(width), static_cast<INT>(height) };

        std::vector<uint8_t> croppedData(width * height * 4);
        m_bitmap->CopyPixels(&rect, width * 4,
            static_cast<UINT32>(croppedData.size()), croppedData.data());

        m_width = width;
        m_height = height;
        m_pixelData = std::move(croppedData);
    }
}
