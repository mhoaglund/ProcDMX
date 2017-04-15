#include <vector>
#include "opencv2/core/core.hpp"

class MultiTrackStereoManager
{
    public:
        MultiTrackStereoManager(const std::string& src1, const std::string& src2);
        int init();
        void updateparam(const std::string& param);
        int run();
        void stop();
        std::vector<TrackedObj> hits;
        bool isRunning;
    private:
        const std::string& Source1;
        const std::string& Source2;
        VideoCapture cap1;
        VideoCapture cap2;
        vector<vector<Point> > contours1_prev; //saving last set of contours to do tracking on
        vector<vector<Point> > contours2_prev;
};

class TrackedObj
{
    public:
        int[] loc;
        int spd;
    private:
        int id;
};