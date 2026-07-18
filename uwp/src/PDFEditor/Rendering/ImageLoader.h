#pragma once

#include "pch.h"

namespace winrt::PDFEditor::Rendering
{
    struct ImageLoader
    {
        ImageLoader();

        bool Initialize();
        void Shutdown();

        bool LoadFromFile(hstring const& filePath);
        bool LoadFromMemory(const uint8_t* data, uint32_t dataSize);
        bool LoadFromResource(int resourceId);

        uint32_t GetWidth() const;
        uint32_t GetHeight() const;
        void* GetPixelData() const;
        Windows::Graphics::Imaging::BitmapPixelFormat GetPixelFormat() const;

        bool SaveToFile(hstring const& filePath);
        Microsoft::UI::Xaml::Media::ImageSource CreateImageSource();

        void Resize(uint32_t newWidth, uint32_t newHeight);
        void Crop(uint32_t x, uint32_t y, uint32_t width, uint32_t height);

    private:
        void EnsureWIC();
        bool CreateBitmapFromFrame();

        winrt::com_ptr<IWICImagingFactory> m_wicFactory;
        winrt::com_ptr<IWICBitmapDecoder> m_decoder;
        winrt::com_ptr<IWICBitmapFrameDecode> m_frame;
        winrt::com_ptr<IWICBitmap> m_bitmap;
        winrt::com_ptr<IWICBitmapScaler> m_scaler;

        uint32_t m_width{ 0 };
        uint32_t m_height{ 0 };
        std::vector<uint8_t> m_pixelData;
        Windows::Graphics::Imaging::BitmapPixelFormat m_pixelFormat{
            Windows::Graphics::Imaging::BitmapPixelFormat::Rgba8 };
    };
}
