def pipeline_branch():
    
    if no more instr to process in micro graphs:
        if num recircs == 0:
            stop search throw exception and return state
        else:
            return num recircs, state
    if num recircs > up: # greater than upper bound which is the number of instructions, so x1 instr per pass
        return infinity, None # it is not a solution
    
    is_wp = for all micro graphs check if there is an instr that is wp

    # two possibilities
    if is_wp:
        # 1. is a new wp
            # 1.1 process wp and add to results
            # 1.2 don't process wp, but process instr, and add to results
        # 2. is not a new wp:
            # 2.1 process all the instrs and if it has a wp consumes it, but no other instrs can be processed here
    else:
        # is not a wp so:
        # 1. This stage is a wp, so continue
        # 2. process instruction and add to results