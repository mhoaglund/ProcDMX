Known functioning performance scenario:
-2 cams, 1280x720 output for each at 14fps
-Resizing feeds to 685 wide
-imshow running every frame on both streams
-Waitkey(10)

85-95% utilization on every core

Known problematic scenarios:
-2 cams, 1280x720 output for each at 14fps
-Resizing feeds to 685 wide
-no gui
-Waitkey(10)

One of the streams instantly crashes, the other is fine