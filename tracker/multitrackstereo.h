#include "opencv2/core/core.hpp"
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/gpu/gpu.hpp"
#include "opencv2/highgui/highgui.hpp"
#include <vector>

class MultiTrackStereoManager
{
    public:
        MultiTrackStereoManager(const std::string& src1, const std::string& src2);
        int init();
        void updateparam(const std::string& param);
        int run();
        void stop();
        //std::vector<TrackedObj> hits;
        bool isRunning;
    private:
        const std::string& Source1;
        const std::string& Source2;
        cv::VideoCapture cap1;
        cv::VideoCapture cap2;
        std::vector<std::vector<cv::Point> > contours1_prev; //saving last set of contours to do tracking on
        std::vector<std::vector<cv::Point> > contours2_prev;
};

class TrackedObj
{
    public:
        int loc;
        int spd;
    private:
        int id;
};
