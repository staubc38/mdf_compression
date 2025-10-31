from pathlib import Path
import os

import asammdf, pandas as pd, numpy as np


sample_mf4_fpa = os.path.join(
    Path(__file__).parent,
    'sample_data.mf4'
)

def generate_sample_data_ints(
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
):
    # we can generate some sample data, 
    # lets do 1000 columns, all i32,
    #   we can mix in some floats later?
    # 1 hour,
    # 400 at 1s, 200 at 0.5s, 200 at 0.25s, 200 at 0.1s
    # see how big that is...

    groups = []  # pd DataFrames

    for sample_interval in sample_intervals_ms:
        r = int(time_s*(1000/sample_interval))
        c = channels_per_interval
        df = pd.DataFrame(
            data=np.random.randint(low=-1024, high=1024, size=(r, c)),
            index=np.array(range(r))*(time_s/r),
            columns=[f'{sample_interval}ms_{n}' for n in range(c)]
        )
        groups.append(df)
    with asammdf.MDF(version='4.10') as mfil:
        for df in groups:
            mfil.append(df)
        mfil.save(sample_mf4_fpa, overwrite=True)

# TODO when ready, mix in some floats, 
#   some 2d data?
#   images?

if __name__ == '__main__':
    generate_sample_data_ints()