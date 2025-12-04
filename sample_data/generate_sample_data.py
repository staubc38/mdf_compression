from pathlib import Path
import os
from io import BytesIO

import asammdf, pandas as pd, numpy as np

def generate_groups_sines(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    channels_per_group=4,

    sfreq = 1,
    samp = 1e10,
    jitter = 1e-2,
    **kwargs
):
    '''
    generate some sine waves with some scale and jitter
    '''
    counter = 1  # oof :(
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        for g in range(int(channels_per_interval/channels_per_group)):
            r = int(time_s*(1000/sample_interval))
            c = channels_per_group

            index = np.array(range(r))*(time_s/r)

            data = {
                f'sine_{sample_interval}ms_{n+counter}': 
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
            counter += c
    return groups

def generate_groups_floats(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    channels_per_group=4,

    flo=-1e10,
    fhi=1e10,
    **kwargs
):
    counter = 1  # oof :(
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        for g in range(int(channels_per_interval/channels_per_group)):
            r = int(time_s*(1000/sample_interval))
            c = channels_per_group
            df = pd.DataFrame(
                data=np.random.uniform(low=flo, high=fhi, size=(r, c)),
                index=np.array(range(r))*(time_s/r),
                columns=[f'float_{sample_interval}ms_{n+counter}' for n in range(c)]
            )
            groups.append(df)
            counter += c
    return groups

def generate_groups_ints(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    channels_per_group=4,

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
    counter = 1  # oof :(
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        for g in range(int(channels_per_interval/channels_per_group)):
            r = int(time_s*(1000/sample_interval))
            c = channels_per_group
            df = pd.DataFrame(
                data=np.random.randint(low=ilo, high=ihi, size=(r, c)),
                index=np.array(range(r))*(time_s/r),
                columns=[f'int_{sample_interval}ms_{n+counter}' for n in range(c)]
            )
            groups.append(df)
            counter += c
    return groups

# TODO when ready, mix in some floats, 
#   some 2d data?
#   images?
def generate_groups_keepalives(
    *a,
    time_s=3600, 
    sample_intervals_ms = (1000, 500, 250, 100),
    channels_per_interval=200,
    channels_per_group=4,

    ilo=-1024,
    ihi=1024,

    include_keepalive=False,

    **kwargs
):
    # i want to include a few channels that "count up"
    #   like a keep-alive signal/counter
    #   0->1->2->3->4->0->1->2->...
    counter = 1  # oof :(
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        for g in range(int(channels_per_interval/channels_per_group)):
            r = int(time_s*(1000/sample_interval))
            c = channels_per_group
            df = pd.DataFrame(
                data=np.ones(shape=(r,c)),
                index=np.array(range(r))*(time_s/r),
                columns=[f'counter_{sample_interval}ms_{n+counter}' for n in range(c)]
            )
            df = (df.cumsum()%10).astype(np.int32)
            groups.append(df)
            counter += c
    return groups

def generate_sample_file(
    fname='sample_data.mf4',
    compression=False,
    
    include_random_ints=False,
    include_random_floats=False,
    include_sine_waves=False,
    include_keepalives=False,
    **kwargs
):
    # support bytesio buffer
    if isinstance(fname, BytesIO):
        fname.seek(0)  # must be!
    elif isinstance(fname, str):   
        fname = os.path.join(
            Path(__file__).parent,
            fname
        )
    else: raise ValueError(f"Only support str or BytesIO for fname, but got {type(fname)}")
    # generate data groups
    groups = []
    if include_random_ints:
        g = generate_groups_ints(**kwargs)
        groups.extend(g)
    if include_random_floats:
        g = generate_groups_floats(**kwargs)
        groups.extend(g)
    if include_sine_waves:
        g = generate_groups_sines(**kwargs)
        groups.extend(g)
    if include_keepalives:
        g = generate_groups_keepalives(**kwargs)
        groups.extend(g)
    print(f"{len(groups)} total groups are generated")
    with asammdf.MDF(version='4.10') as mfil:
        for df in groups:
            mfil.append(df)
        mfil.save(fname, overwrite=True, compression=compression)

if __name__ == '__main__':
    generate_sample_file()