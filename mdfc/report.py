'''
just want to be able to generate a "compression results" report

TODO:
- when estimating the uncompressed MDF size, 
    from the mdfc file metadata only,
    it does not properly account for the groups
    ie do not count the times for each signal, it should be for each group

'''

from .decompressor import MDFDecompressor
from copy import deepcopy
import pandas as pd
def generate_compression_report(mdfc_file_path):
    '''
    just want to be able to make some quick summaries
    '''
    with MDFDecompressor(mdfc_file_path, 
        load_time_axis_on_enter=False, 
        close_file_on_exit=False
    ) as dfil:
        md = deepcopy(dfil.metadata)
        tmd = deepcopy(dfil.time_metadata)

    # we can make a couple dataframes i guess
    md = pd.DataFrame.from_dict(md, orient='index')  # dict of dict
    # the index is the signal name (key value)

    # time elems is the first element in dshape (should be a list)
    time_elems = md['dshape'].str[0].astype(pd.Int64Dtype())
    md['time_elems'] = time_elems
    # total elems is product of dshape (should be a list)
    total_elems = md['dshape'].explode()
    total_elems = pd.to_numeric(total_elems.groupby(total_elems.index).prod(), errors='coerce')
    md['total_elems'] = total_elems

    # assume dtype has the bit size as its number
    # eg float64, int32, ...
    #   TODO this may require change if we change the source of dtype
    bitsize = md['dtype'].str.extract(r'(\d+)').astype(pd.Int64Dtype())
    if isinstance(bitsize, pd.DataFrame):
        # extract seems to make a dataframe, 
        #   which i guess makes sense since there could 
        #   be multiple regex groups?
        bitsize = bitsize[bitsize.columns[0]]
    md['bitsize'] = bitsize

    # high level summary
    md['time_uncompressed_size'] = md['time_elems']*64/8
    md['samples_uncompressed_size'] = md['total_elems']*md['bitsize']
    md = md.rename(columns={
            'csize': 'samples_compressed_size',
            'csize_t': 'time_compressed_size'
        }
    )
    summary = md.groupby('dtype').agg(
        {
            'time_uncompressed_size': 'sum',
            'samples_uncompressed_size': 'sum',
            'samples_compressed_size': 'sum',
            'time_compressed_size': 'sum',
        }
    ).T
    # include the time axis
    try:
        int_col = next(c for c in summary.columns if 'int' in c)
    except StopIteration:
        int_col = summary.columns[0]
    summary.loc['time_axis_compressed_size', int_col] = float(tmd[1])

    # this is a bit wrong... seems MDF might save with a bit lower size
    #   can be improved when we add MDF metadata
    overall_cr = (
        (
            summary.loc["samples_compressed_size", :].sum() + 
            summary.loc["time_compressed_size", :].sum() + 
            summary.loc["time_axis_compressed_size", :].sum()
        ) / 
        (
            summary.loc["time_uncompressed_size", :].sum() + 
            summary.loc["samples_uncompressed_size", :].sum()
        )
    )
    print('Estimated overall compression ratio vs uncompressed MDF: '
         f'{overall_cr:e}, or {(1/overall_cr):.2f}x'
    )
    return summary, md
