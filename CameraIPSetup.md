Setting up DHCP and Static IPs for cameras:

In this installation, the jetson has an extra LAN card for SSH access. The main gigabit interface on the board is being used to handle the cameras on an ad-hoc intranet.

Running isc-dhcp-server on eth0.
See included dhcpd.conf for meaningful config and reservations.
Run sudo update-rc.d isc-dhcp-server enable to include it in the boot process.'

Configure NetworkManager on Ubuntu:
Add a static ipv4 address to the interface the dhcp server is running on.
The static address for this interface should make sense in relation to the range that its dhcp will give out, but not be included in that range.
I chose 10.254.239.1 to match the {option routers} item in dhcpd.conf.

Also, see: https://ubuntuforums.org/showthread.php?t=2068111
I had this issue with the tk1. When isc-dhcp attempted to start on boot, the interface wasn't ready yet.
I followed the idea in that thread- added a dependency check to the first line of isc-dhcp-server.conf in init.d
Worked great.

Configure the cameras:
With a brand new camera, hook it up to a network you can use to access it. Determine the IP the camera was given, and browse to that.
Which position will this camera occupy? Cam1 looks toward the river. Cam2 looks away from the river. After figuring out the name of the camera,
look again in dhcpd.conf. The name will match one of the fixed-address hosts that has been configured there. Find the ip in that host.
Back in the camera portal, go to Parameters -> IP Settings. Set the IP type to Fixed IP, enter the fixed-address you found in dhcpd.conf,
and enter the subnet mask (netmask) and gateway (router) that match those values found in dhcpd. DNS type should remain "from DHCP".
Hit apply. The camera should redirect you to its new IP once it gets it from dhcp.

These fixed addresses are hard coded into the CV software, so adhering to them and using them properly is critical.

To configure the camera's media output:
In the camera portal, go to Media -> Video. The main stream should be set like the following:
Resolution: 1280x720
Bit Rate: 5120
Maximum Frame: 20
Bit Rate Type: Constant Bit Rate
Frame Gap: 25

Hit Apply. The camera will reboot.

SSH and Opening Camera Feeds from the ground:
We'll run a cat5 line from the PoE switch to the access box on the ground.
Since eth0, the interface DHCP is running on, has a static IP, we can start an SSH session against that IP to ssh into the Jetson.
Also, we'll be on the same network as the cameras in this configuration, so we can browse to their IPs and get the feed from the ground.



