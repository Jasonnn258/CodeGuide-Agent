# Pipeline builder only runs the first step

`build_pipeline` should chain every step so each step receives the output of the previous step, but the loop exits after the first iteration.
