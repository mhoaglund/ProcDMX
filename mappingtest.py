
ARR= [0,0,0,0,0,1,1,1,0,1,0,1,0,1,1,1,1,0,0,0,1,1,1,0,1]

def groom(_list):
    """Given an array of readings, fill in obvious gaps and spot edges"""
    listsz = len(_list)
    islands = []
    pits = []
    holes = []
    edges = []
    contigs = []
    curr = []
    currpits = []
    #find contiguous regions of positive values and log them by index
    for value in range(0, listsz):
        if _list[value] == 0:
            if len(currpits) > 0:
                currpits.append(value)
            if len(currpits) == 0:
                currpits = []
                currpits.append(value)
            if len(curr) == 0:
                continue
            if len(curr) > 0:
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

        if _list[value] > 0:
            if len(curr) > 0:
                curr.append(value)
            if len(curr) == 0:
                curr.append(value)

            if len(currpits) > 0:
                if len(currpits) > 1:
                    pits.append(currpits)
                else:
                    holes.append(currpits)
                currpits = []

    if len(currpits) > 0:
        if len(currpits) > 1:
            pits.append(currpits)
        else:
            holes.append(currpits)
        currpits = []

    if len(curr) > 0:
        if len(curr) > 1:
            contigs.append(curr)
        else:
            islands.append(curr)
        curr = []


    print islands
    print edges
    print contigs
    print pits
    print holes

groom(ARR)