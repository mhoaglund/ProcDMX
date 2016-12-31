
ARR= [0,0,0,0,0,1,1,1,0,1,0,1,0,1,1,1,1,0,0,0,1,1,1,0,1]

def groom(_list):
    """Given an array of readings, fill in obvious gaps and spot edges"""
    listsz = len(_list)-1
    islands = []
    edges = []
    contigs = []
    curr = []
    #find contiguous regions of positive values and log them by index
    for value in range(0, listsz):
        if _list[value] == 0 and len(curr) == 0:
            continue
        elif _list[value] == 0 and len(curr) > 0:
            if len(curr) > 1:
                contigs.append(curr)
                edgepair = []
                if curr[0] > 0:
                    edgepair.append(curr[0]-1)
                if curr[len(curr)-1] < listsz:
                    edgepair.append(curr[len(curr)-1]+1)
                if len(edgepair) > 1:
                    edges.append(edgepair)
            else:
                islands.append(curr)
            curr = []
        elif _list[value] > 0 and len(curr) > 0:
            curr.append(value)
        elif _list[value] > 0 and len(curr) == 0:
            #start a new contiguous region
            curr = [] #superstition
            curr.append(value)
    print islands
    print edges
    print contigs

groom(ARR)