#Needs:

#Receipt method that receives an array from a sensor and patches it into the 'live' one

#Reboot signal method (might not be possible, not sure)

#Warning method for logging the addys of nodes that havent been tripped in a while
#to mark them for maintenance attention

#possible sensor report format: Sender ID, speed int (low res), rising or falling direction

#Intent: match sensor nodes to lights
RenderMap = {
    1: [0,1,2,3],
    2: [4,5,6,7],
    3: [8,9,10,11],
    4: [12,13,14,15],
    5: [16,17,18,19],
    6: [20,21,22,23],
    7: [24,25,26,27]
}

#we'll divide intensity readings by this
Intensity_Modifier = 10
#we'll multiply channel modifiers by this to ease spatially
Intensity_Dropoff = 0.5

Default_Color = [125,125,25,75]
Default_Modifier_Bias = [15,15,50,50] #will be multiplying intensity modifiers by this, basically...

# Intent: catch a sensor packet and create a set of channel modifiers to be layered onto the universe in another function
def RenderReading(senderId, dir, intensity):
    global RenderMap
    global Intensity_Modifier
    targetLights = RenderMap[senderId] #grab a list of lights that correspond to the sensor that spoke
    outputLayer = {}
    intensity_change = intensity/Intensity_Modifier
    base_intensity = Default_Modifier_Bias * intensity_change
    for light in range(len(targetLights)):
        #first_index = targetLights[i] #the first channel for the light we're working on
        if i == 0 or i == len(targetLights):
            channels = base_intensity * Intensity_Dropoff
            for channel in channels:
                outputLayer.append(channel)
        else:
            for channel in base_intensity:
                outputLayer.append(channel)

#The fun part. Given a set of channel modifiers, squish them down into eachother so we have on summed-up reading for each channel.
#at some point, figuring out when in time to do this will be important.
def MergeModifiers():

            


