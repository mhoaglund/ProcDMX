#include "opencv2/core/core.hpp"
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/gpu/gpu.hpp"
#include "opencv2/highgui/highgui.hpp"
#include <stdio.h>
#include "multitrackstereo.h"
//A glorified opencv sample here. This doesn't actually have to do much- it just has to track pedestrians and spit out metrics
//that get fed to python through a wrapper.
using namespace std;
using namespace cv;
using namespace cv::gpu;

TrackedObj::TrackedObj(){

}

MultiTrackStereoManager::MultiTrackStereoManager(const std::string& src1, const std::string& src2){
    Source1 = src1;
    Source2 = src2;
}

int MultiTrackStereoManager::init(){
	cap1.open(Source1);
	cap2.open(Source2);
    bool update_bg_model = true;

    if( !cap1.isOpened() | !cap2.isOpened())
    {
        printf("Unable to open one or both camera feeds.");
        return -1;
    }
    else return 1;
}

int MultiTrackStereoManager::run(){
    isRunning = true;

    namedWindow("image1", WINDOW_NORMAL);
    namedWindow("foreground1", WINDOW_NORMAL);
    namedWindow("image2", WINDOW_NORMAL);
    namedWindow("foreground2", WINDOW_NORMAL);

    MOG2_GPU bg_model1;//(100, 3, 0.3, 5);
    MOG2_GPU bg_model2;//(100, 3, 0.3, 5);
    int threshold_value = 0;
    int threshold_type = 3;
    int const max_BINARY_value = 255;

    Mat img1, fgmask1, fgimg1, bgimg1;
    Mat img2, fgmask2, fgimg2, bgimg2;
    GpuMat d_img1(img1);
    GpuMat d_fgmask1(fgmask1);
    GpuMat d_fgimg1(fgimg1);
    GpuMat d_bgimg1(bgimg1);
    GpuMat d_img2(img2);
    GpuMat d_fgmask2(fgmask2);
    GpuMat d_fgimg2(fgimg2);
    GpuMat d_bgimg2(bgimg2);

    while(isRunning){
        cap1 >> img1;
        cap2 >> img2;
        if( img1.empty() | img2.empty() )
            break;
        Mat gsimg1;
            cvtColor(img1, gsimg1, COLOR_BGR2GRAY);
            d_img1.upload(gsimg1);
        Mat gsimg2;
            cvtColor(img2, gsimg2, COLOR_BGR2GRAY);
            d_img2.upload(gsimg2);

        if( fgimg1.empty() )
            fgimg1.create(img1.size(), gsimg1.type());
        if( fgimg2.empty() )
            fgimg2.create(img2.size(), gsimg2.type());

        bg_model1(d_img1, d_fgmask1, update_bg_model ? -1 : 0);
	    bg_model1.getBackgroundImage(d_bgimg1);
        bg_model2(d_img2, d_fgmask2, update_bg_model ? -1 : 0);
	    bg_model2.getBackgroundImage(d_bgimg2);

        gpu::blur(d_fgimg1, d_fgimg1, cv::Size(7, 7));
        gpu::blur(d_fgimg2, d_fgimg2, cv::Size(7, 7));
        gpu::threshold( d_fgimg1, d_fgimg1, threshold_value, max_BINARY_value,threshold_type );
        gpu::threshold( d_fgimg2, d_fgimg2, threshold_value, max_BINARY_value,threshold_type );

        d_fgmask1.download(fgmask1);
        d_fgimg1.download(fgimg1);
        d_fgmask2.download(fgmask2);
        d_fgimg2.download(fgimg2);

        vector<vector<Point> > contours1;
        vector<Vec4i> hierarchy1;
        vector<vector<Point> > contours2;
        vector<Vec4i> hierarchy2;
        findContours( fgimg1, contours1, hierarchy1, CV_RETR_EXTERNAL, CV_CHAIN_APPROX_SIMPLE, Point(0, 0) );
        findContours( fgimg2, contours2, hierarchy2, CV_RETR_EXTERNAL, CV_CHAIN_APPROX_SIMPLE, Point(0, 0) );

        for(int i = 0; i<contours1.size(); i++){
            drawContours( gsimg1, contours1, i, (0,255,0), 2, 8, hierarchy1, 0, Point() );
        }
        for(int j = 0; j<contours1.size(); j++){
            drawContours( gsimg2, contours2, j, (0,255,0), 2, 8, hierarchy2, 0, Point() );
        }

        if(!d_bgimg1.empty() & !d_bgimg2.empty())
            d_bgimg1.download(bgimg1);
            d_bgimg2.download(bgimg2);

            imshow("image1", gsimg1);
            imshow("foreground1", fgimg1);
            imshow("image2", gsimg2);
            imshow("foreground2", fgimg2);
        }
    }
    return 0;
}

int MultiTrackStereoManager::runFrame(VideoCapture _cap){

}

///Release streams and stop run loop
MultiTrackStereoManager::stop(){
    isRunning = false;
    cap1.release();
    cap2.release();
}
