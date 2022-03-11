import datetime
import io
import unittest

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from notifybot.libs import heatmap


np.random.seed(sum(map(ord, 'calmap')))


class KusaDataConverterTest(unittest.TestCase):
    def test_convert(self):
        today = datetime.date(year=2021, month=5, day=18)
        all_days = pd.date_range(end=today, periods=365, freq='D')
        days = np.random.choice(all_days, 96, replace=False)
        events = pd.Series(np.random.randint(0, 24, len(days)),
                           index=days, dtype=np.int8)

        converter = heatmap.KusaDataConverter(events)
        self.assertIsInstance(converter, heatmap.KusaDataConverter)

        converter.data_shaping()
        by_day = converter.by_day
        plot_data = converter.plot_data
        fill_data = converter.fill_data
        self.assertIsInstance(by_day, pd.DataFrame)
        self.assertIsInstance(plot_data, np.ma.MaskedArray)
        self.assertIsInstance(fill_data, np.ma.MaskedArray)

        self.assertEqual(plot_data.shape, fill_data.shape)

        one_dim_data = plot_data[::-1].T.reshape(
            (plot_data.shape[0] * plot_data.shape[1],))
        self.assertLessEqual(len(by_day["data"]), len(one_dim_data))
        for i, v in enumerate(by_day["data"].values):
            if pd.isnull(v):
                self.assertIs(one_dim_data[i], np.ma.masked)
            else:
                self.assertEqual(v, one_dim_data[i])

    def test_start_with_Sunday(self):
        data = list(range(5))
        days = pd.date_range(end=datetime.datetime(
            year=2021, month=5, day=18), periods=5, freq='D')
        events = pd.Series(data, index=days)

        end_date = days[-1]
        converter = heatmap.KusaDataConverter(events, end_date=end_date)
        converter.data_shaping()
        self.assertEqual(converter.by_day["day"][0], 0)
        self.assertLess(converter.by_day.index[0], end_date)

    def test_end_date(self):
        data = list(range(5))
        days = pd.date_range(end=datetime.datetime(
            year=2021, month=5, day=18), periods=5, freq='D')
        events = pd.Series(data, index=days)

        end_date = datetime.datetime(
            year=2021, month=5, day=17).date()
        converter = heatmap.KusaDataConverter(
            events, end_date=end_date)
        converter.data_shaping()
        self.assertEqual(converter.by_day.index[-1], end_date)


class HeatMapTest(unittest.TestCase):
    def test_create_heatmap(self):
        # png形式で画像が保存されるか確認
        all_days = pd.date_range(end='3/15/2021', periods=365, freq='D')
        days = np.random.choice(all_days, 96, replace=False)
        events = pd.Series(np.random.randint(0, 24, len(days)),
                           index=days, dtype=np.int8)
        hm = heatmap.HeatMap(events)
        ax = hm.plot(vmin=0, vmax=24, linewidth=1)
        sio = io.BytesIO()
        format = "png"
        plt.savefig(sio, format=format)
        sio.seek(0)
        bline = sio.readline()
        self.assertTrue(bline.startswith(b'\x89PNG\r\n'))
