from pathlib import Path
import os

import asammdf, pandas as pd, numpy as np

def generate_groups_sines(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    sfreq = 1,
    samp = 1e10,
    jitter = 1e-2,
    **kwargs
):
    '''
    generate some sine waves with some scale and jitter
    '''
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        r = int(time_s*(1000/sample_interval))
        c = channels_per_interval

        index = np.array(range(r))*(time_s/r)

        data = {
            f'sine_{sample_interval}ms_{n}': 
            (
                np.sin(2*np.pi*index/sample_interval) +
                ((np.random.rand(len(index))*2*jitter)-jitter)
            )
            for n in range(c)
        }
        df = pd.DataFrame(
            data=data,
            index=index,
        )
        groups.append(df)
    return groups

def generate_groups_floats(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    flo=-1e10,
    fhi=1e10,
    **kwargs
):
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        r = int(time_s*(1000/sample_interval))
        c = channels_per_interval
        df = pd.DataFrame(
            data=np.random.uniform(low=flo, high=fhi, size=(r, c)),
            index=np.array(range(r))*(time_s/r),
            columns=[f'float_{sample_interval}ms_{n}' for n in range(c)]
        )
        groups.append(df)
    return groups

def generate_groups_ints(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,

    ilo=-1024,
    ihi=1024,

    include_keepalive=False,

    **kwargs
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
            data=np.random.randint(low=ilo, high=ihi, size=(r, c)),
            index=np.array(range(r))*(time_s/r),
            columns=[f'int_{sample_interval}ms_{n}' for n in range(c)]
        )
        groups.append(df)

        # i want to include a few channels that "count up"
        #   like a keep-alive signal/counter
        #   0->1->2->3->4->0->1->2->...
        if include_keepalive:
            c = 10
            df = pd.DataFrame(
                data=np.ones(shape=(r,c)),
                index=df.index,  # first index
                columns=[f'counter_{sample_interval}ms_{n}' for n in range(c)]
            )
            df = (df.cumsum()%10).astype(np.int32)
            groups.append(df)
    return groups

# TODO when ready, mix in some floats, 
#   some 2d data?
#   images?

def generate_sample_file(
    fname='sample_data.mf4',
    compression=False,
    
    include_ints=True,
    include_floats=True,
    include_sines=True,
    **kwargs
):
    sample_mf4_fpa = os.path.join(
        Path(__file__).parent,
        fname
    )
    # generate data groups
    groups = []
    if include_ints:
        g = generate_groups_ints(**kwargs)
        groups.extend(g)
    if include_floats:
        g = generate_groups_floats(**kwargs)
        groups.extend(g)
    if include_sines:
        g = generate_groups_sines(**kwargs)
        groups.extend(g)
    with asammdf.MDF(version='4.10') as mfil:
        for df in groups:
            mfil.append(df)
        mfil.save(sample_mf4_fpa, overwrite=True, compression=compression)

if __name__ == '__main__':
    generate_sample_file()