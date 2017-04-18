#include "opencv2/core/core.hpp"
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/gpu/gpu.hpp"
#include "opencv2/highgui/highgui.hpp"
#include <vector>

class MultiTrackStereoManager
{
    public:
        MultiTrackStereoManager(std::string src1, std::string src2);
        int init();
        void updateparam(std::string param);
        int run();
        void stop_capture();
        //std::vector<TrackedObj> hits;
        bool isRunning;
    private:
        std::string Source1;
        std::string Source2;
        cv::VideoCapture cap1;
        cv::VideoCapture cap2;
        std::vector<std::vector<cv::Point> > contours1_prev; //saving last set of contours to do tracking on
        std::vector<std::vector<cv::Point> > contours2_prev;
        int runFrame(cv::VideoCapture _capture);
};

class TrackedObj
{
    public:
	TrackedObj(int _x, int _y);
        int loc[2];
        int spd;
    private:
        int id;
};
