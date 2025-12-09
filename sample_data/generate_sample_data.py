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

    samp = 10,
    jitter = 1e-2,
    jitter_time=False,

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

            time = np.array(range(r))*(time_s/r)
            if jitter_time:
                if jitter_time is True: jitter_time = 0.05
                # +/- 5% jitter
                jtime = (
                    ((np.random.randint(
                        0, 200,
                        size=len(time)
                    ) - 100)/100)
                     * (sample_interval*jitter_time/1000)
                )
                time += jtime
                if time[0] < 0: time -= time[0]
                elif time[0] > 0: time += time[0]
                else: pass
            data = {
                f'sine_{sample_interval}ms_{n+counter}': 
                (
                    np.sin(2*np.pi*time/sample_interval)*samp +
                    ((np.random.rand(len(time))*2*jitter)-jitter)
                )
                for n in range(c)
            }
            df = pd.DataFrame(
                data=data,
                index=time,
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
    jitter_time=False,

    **kwargs
):
    counter = 1  # oof :(
    groups = []  # pd DataFrames
    for sample_interval in sample_intervals_ms:
        for g in range(int(channels_per_interval/channels_per_group)):
            r = int(time_s*(1000/sample_interval))
            c = channels_per_group

            if jitter_time:
                if jitter_time is True: jitter_time = 0.05
                # +/- 5% jitter
                jtime = (
                    ((np.random.randint(
                        0, 200,
                        size=len(time)
                    ) - 100)/100)
                     * (sample_interval*jitter_time/1000)
                )
                time += jtime
                if time[0] < 0: time -= time[0]
                elif time[0] > 0: time += time[0]
                else: pass
            df = pd.DataFrame(
                data=np.random.uniform(low=flo, high=fhi, size=(r, c)),
                index=time,
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
    jitter_time=False,

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

            time = np.array(range(r))*(time_s/r)
            if jitter_time:
                if jitter_time is True: jitter_time = 0.05
                # +/- 5% jitter
                jtime = (
                    ((np.random.randint(
                        0, 200,
                        size=len(time)
                    ) - 100)/100)
                     * (sample_interval*jitter_time/1000)
                )
                time += jtime
                if time[0] < 0: time -= time[0]
                elif time[0] > 0: time += time[0]
                else: pass
            df = pd.DataFrame(
                data=np.random.randint(low=ilo, high=ihi, size=(r, c)),
                index=time,
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
    jitter_time=False,

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

            time = np.array(range(r))*(time_s/r)
            if jitter_time:
                if jitter_time is True: jitter_time = 0.05
                # +/- 5% jitter
                jtime = (
                    ((np.random.randint(
                        0, 200,
                        size=len(time)
                    ) - 100)/100)
                     * (sample_interval*jitter_time/1000)
                )
                time += jtime
                if time[0] < 0: time -= time[0]
                elif time[0] > 0: time += time[0]
                else: pass
            df = pd.DataFrame(
                data=np.ones(shape=(r,c)),
                index=time,
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