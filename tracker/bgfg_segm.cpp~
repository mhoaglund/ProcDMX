#include "opencv2/core/core.hpp"
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/gpu/gpu.hpp"
#include "opencv2/highgui/highgui.hpp"
#include <stdio.h>
//A glorified opencv sample here. This doesn't actually have to do much- it just has to track pedestrians and spit out metrics
//that get fed to python through a wrapper.
using namespace std;
using namespace cv;
using namespace cv::gpu;

static void help()
{
 printf("\nDo background segmentation, especially demonstrating the use of cvUpdateBGStatModel().\n"
"Learns the background at the start and then segments.\n"
"Learning is togged by the space key. Will read from file or camera\n"
"Usage: \n"
"			./bgfg_segm [--camera]=<use camera, if this key is present>, [--file_name]=<path to movie file> \n\n");
}

const char* keys =
{
    "{c |camera   |true    | use camera or not}"
    "{fn|file_name|tree.avi | movie file             }"
};

//this is a sample for foreground detection functions
int main(int argc, const char** argv)
{
    help();

    CommandLineParser parser(argc, argv, keys);
    bool useCamera = parser.get<bool>("camera");
    string file = parser.get<string>("file_name");
    VideoCapture cap;
	cap.open("rtsp://192.168.0.29:554/12.cgi");
    bool update_bg_model = true;

    //if( useCamera ){
	//cap.open("rtsp://192.168.0.29:554/12.cgi");
	//}
    //else
    //    cap.open(file.c_str());
    parser.printParams();

    if( !cap.isOpened() )
    {
        printf("can not open camera or video file\n");
        return -1;
    }

    namedWindow("image", WINDOW_NORMAL);
    namedWindow("foreground mask", WINDOW_NORMAL);
    namedWindow("foreground image", WINDOW_NORMAL);
    namedWindow("mean background image", WINDOW_NORMAL);

    MOG2_GPU bg_model;//(100, 3, 0.3, 5);

    Mat img, fgmask, fgimg, bgimg;
    GpuMat d_img(img);
    GpuMat d_fgmask(fgmask);
    GpuMat d_fgimg(fgimg);
    GpuMat d_bgimg(bgimg);

    for(;;)
    {
        cap >> img;

        if( img.empty() )
            break;
	Mat gsimg;
        cvtColor(img, gsimg, COLOR_BGR2GRAY);

	d_img.upload(gsimg);
	
    if( fgimg.empty() )
        fgimg.create(img.size(), gsimg.type());

    bg_model(d_img, d_fgmask, update_bg_model ? -1 : 0);
	bg_model.getBackgroundImage(d_bgimg);

        d_fgimg = Scalar::all(0);
        d_img.copyTo(d_fgimg, d_fgmask);

	d_fgmask.download(fgmask);
	d_fgimg.download(fgimg);
	if(!d_bgimg.empty())
		d_bgimg.download(bgimg);

        imshow("image", gsimg);
        imshow("foreground mask", fgmask);
        imshow("foreground image", fgimg);
        if(!bgimg.empty())
          imshow("mean background image", bgimg );

        char k = (char)waitKey(30);
        if( k == 27 ) break;
        if( k == ' ' )
        {
            update_bg_model = !update_bg_model;
            if(update_bg_model)
                printf("Background update is on\n");
            else
                printf("Background update is off\n");
        }
    }

    return 0;
}
