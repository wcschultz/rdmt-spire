import asdf

from ..monitors.astrometry import AstrometryMonitor


def test_monitor_astrometry():
    """
    Testing class Astrometry    
    """
    af=asdf.AsdfFile()
    monitor=AstrometryMonitor(af, datadir="")
    monitor.run()
    for log in monitor.log:
        print(log)
    data_cards=monitor.get_data_card('all')
    assert len(data_cards) == 2

    assert data_cards[0].monitor_name == 'astrometry'
    if af.uri is None:
        assert data_cards[0].filename == ''
    else:
        assert data_cards[0].filename == af['roman']['meta']['filename']
    assert data_cards[0].data_name == 'astrometric_offset'
    assert data_cards[0].data_unit == 'arcsec'

    assert data_cards[1].data_name == 'num_astrometric_sources'
    assert data_cards[1].data_unit == ''