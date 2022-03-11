import calendar
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ColorConverter, ListedColormap


class KusaDataConverter:
    """草画像生成のために必要なデータを整形するクラス

    プロット用のDataFrameとnp配列と背景用のデータを作成する


    Attributes:
        data (pandas.Series): 通話時間を格納したSeries
        end_data (datetime.date): 生成するデータの最終日
    """

    def __init__(self,
                 data: pd.Series,
                 end_date: Optional[date] = None) -> None:
        self.data: pd.Series = data
        self.end_date: Optional[date] = end_date

    def data_shaping(self) -> None:
        """データを整形する
        """
        by_day: pd.Series = self.data

        if self.end_date is None:
            self.end_date = sorted(by_day.index)[-1].date()

        start_date: date = self.end_date - timedelta(days=365)

        if start_date.weekday() != 6:
            # dayが6で始まるようにする(日曜始まり)
            substance: int = start_date.weekday() + 1
            start_date -= timedelta(days=substance)

        # 存在しないインデックスをNaNで埋める
        by_day = by_day.reindex(
            pd.date_range(
                start=start_date, end=self.end_date, freq="D"),
        )

        # 週の相対値を作成
        weeks: list = []
        for week in range(len(by_day)//7):
            weeks += [week]*7
        weeks += [len(by_day)//7] * (len(by_day) % 7)

        # np配列作成用のデータフレーム
        self.by_day: pd.DataFrame = pd.DataFrame(
            {
                "data": by_day,
                "fill": 1,
                "day": (by_day.index.dayofweek + 1) % 7,
                "week": weeks
            }
        )

        # NaNをマスクしたMaskedArrayを生成
        plot_data: np.ndarray = self.by_day.pivot(
            "day", "week", "data").values[::-1]
        self.plot_data: np.ma.MaskedArray = np.ma.masked_where(
            np.isnan(plot_data), plot_data)

        # 背景用のMaskedArrayを生成
        fill_data: np.ndarray = self.by_day.pivot(
            "day", "week", "fill").values[::-1]
        self.fill_data: np.ma.MaskedArray = np.ma.masked_where(
            np.isnan(fill_data), fill_data)


# https://github.com/martijnvermaat/calmap をベースに作られている
class HeatMap:
    """草画像を生成するクラス

    Attributes:
        data (pandas.Series): 通話時間を格納したSeries
        end_data (datetime.date): 生成するデータの最終日
    """

    def __init__(self, data: pd.Series, end_date: Optional[date] = None) -> None:
        self.data: pd.Series = data
        self.end_date: Optional[date] = end_date

        converter = KusaDataConverter(data, end_date=self.end_date)
        converter.data_shaping()
        self.by_day: pd.DataFrame = converter.by_day
        self.plot_data: np.ma.MaskedArray = converter.plot_data
        self.fill_data: np.ma.MaskedArray = converter.fill_data

    def plot(self,
             vmin: Union[int, float, None] = None,
             vmax: Union[int, float, None] = None,
             cmap: str = 'YlGn',
             fillcolor: str = "whitesmoke",
             linewidth: int = 1,
             linecolor: Optional[str] = None,
             daylabels: Any = calendar.day_abbr[:],
             monthlabels: Any = calendar.month_abbr[1:],
             ax: Optional[plt.axes] = None,
             **kwargs) -> plt.axes:
        """整形したデータから草画像を生成する

        Args:
            vmin (Union[int, float, None], optional): データの最小値. Defaults to None.
            vmax (Union[int, float, None], optional): データの最大値. Defaults to None.
            cmap (str, optional): ヒートマップのカラーマップ. Defaults to 'YlGn'.
            fillcolor (str, optional): 背景用の色. Defaults to "whitesmoke".
            linewidth (int, optional): 線の幅. Defaults to 1.
            linecolor (Optional[str], optional): 線の色. Defaults to None.
            daylabels (Any, optional): 曜日ラベル. Defaults to calendar.day_abbr[:].
            monthlabels (Any, optional): 月ラベル. Defaults to calendar.month_abbr[1:].
            ax (Optional[plt.axes], optional): 描画するaxes. Defaults to None.

        Returns:
            plt.axes: 草画像を描画したaxes
        """

        # Min and max per day.
        if vmin is None:
            vmin = self.by_day.min()
        if vmax is None:
            vmax = self.by_day.max()

        if ax is None:
            ax = plt.gca()

        if linecolor is None:
            # Unfortunately, linecolor cannot be transparent, as it is drawn on
            # top of the heatmap cells. Therefore it is only possible to mimic
            # transparent lines by setting them to the axes background color. This
            # of course won't work when the axes itself has a transparent
            # background so in that case we default to white which will usually be
            # the figure or canvas background color.
            linecolor = ax.get_facecolor()
            if ColorConverter().to_rgba(linecolor)[-1] == 0:
                linecolor = "white"

        # Draw heatmap for all days of the year with fill color.
        ax.pcolormesh(self.fill_data, vmin=0, vmax=1,
                      cmap=ListedColormap([fillcolor]))

        # Draw heatmap.
        kwargs["linewidth"] = linewidth
        kwargs["edgecolors"] = linecolor
        ax.pcolormesh(self.plot_data, vmin=vmin,
                      vmax=vmax, cmap=cmap, **kwargs)

        # Limit heatmap to our data.
        ax.set(xlim=(0, self.plot_data.shape[1]), ylim=(
            0, self.plot_data.shape[0]))

        # Square cells.
        ax.set_aspect("equal")

        # Remove spines and ticks.
        for side in ("top", "right", "left", "bottom"):
            ax.spines[side].set_visible(False)
        ax.xaxis.set_tick_params(which="both", length=0)
        ax.xaxis.set_ticks_position('top')
        ax.yaxis.set_tick_params(which="both", length=0)
        ax.yaxis.set_ticks_position('left')

        # Get indices for monthlabels.
        start_month: int = self.by_day.index[0].month - 1
        monthlabels = monthlabels[start_month:] + \
            monthlabels[:start_month]

        # Get indices for daylabels.
        dayticks: Iterable[int] = range(len(daylabels))

        ax.set_xlabel("")
        xticks = [0]
        last_month = None
        for i, weekstart in enumerate(self.by_day[self.by_day['day'] == 0].index):
            # 日曜日の月が変わるx座標にtickを配置
            if last_month is None:
                last_month = weekstart.month
            elif last_month != weekstart.month:
                xticks.append(i)
                last_month = weekstart.month

        ax.set_xticks(xticks)
        ax.set_xticklabels([monthlabels[i % 12]
                            for i in range(len(xticks))], ha="left")

        ax.set_ylabel("")
        ax.set_yticks([6 - i + 0.5 for i in dayticks])
        ax.set_yticklabels(
            ["", "Mon", "", "Wed", "", "Fri", ""], rotation="horizontal", va="center"
        )
        return ax


def dt_to_str(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d')
