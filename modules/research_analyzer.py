import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set(rc={"figure.figsize": (60, 30)})
stop = False
txt = (20, 1)
txt2 = (7, 1)
btn = (25, 1)


def plot_temp(plot_cols, df):
    from matplotlib import pyplot as plt
    import seaborn as sns

    sns.set()
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(projection="3d")
    # colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
    values = plot_cols
    ax.scatter(
        xs=df[values[0]],
        ys=df[values[1]],
        zs=df[values[2]],
        s=40,
        depthshade=True,
        color="red",
        linewidth=0,
    )
    ax.set_ylim(max(df[plot_cols[1]]), 0)
    ax.set_xlim(0, max(df[plot_cols[0]]))
    ax.set_xlabel(values[0])
    ax.set_ylabel(values[1])
    ax.set_zlabel(values[2])
    ax.view_init(5, -70)
    plt.tight_layout()
    # plt.show()
    plt.savefig("plot.png")
    plt.close()
    return None


def plot_temp_old(plot_cols, f, pivot):
    sns.relplot(
        x=plot_cols[0],
        y=plot_cols[1],
        data=f,
        hue=plot_cols[2],
        size=plot_cols[3],
        style=plot_cols[4],
        col=plot_cols[5],
    )
    plt.suptitle("All sales")
    # plt.show()
    plt.savefig("plot.png")
    plt.close()
    sns.relplot(
        x=plot_cols[0],
        y=plot_cols[1],
        data=pivot,
        hue=plot_cols[2],
        size=plot_cols[3],
        style=plot_cols[4],
        col=plot_cols[5],
    )
    plt.suptitle("Average sales")
    # plt.show()
    plt.savefig("plot2.png")
    plt.close()
    return None


def relplot_cols(x, y, hue, size, style, col):
    if hue == "":
        hue = None
    if size == "":
        size = None
    if style == "":
        style = None
    if col == "":
        col = None
    return list([x, y, hue, size, style, col])


def read_file():
    file = sg.PopupGetFile("Select the research file")
    try:
        source = pd.ExcelFile(file)
    except:
        sg.PopupError("Wrong file selected")
        return None

    sheets = source.sheet_names
    event, sheet = sg.Window(
        "Select data sheet",
        layout=[
            [
                sg.DropDown(
                    sheets, default_value=sheets[0], size=btn, change_submits=True
                )
            ]
        ],
        size=(300, 50),
    ).read(close=True)
    f = pd.read_excel(source, sheet_name=sheet[0])
    return f


def create_data_cols(f):
    cols = f.columns.tolist()

    event, d_cols = sg.Window(
        "Select data columns",
        layout=[
            [
                sg.Text("Sales monthly", s=txt),
                sg.DropDown(cols, key="SM", default_value="Sales"),
            ],
            [
                sg.Text("Sales daily", s=txt),
                sg.DropDown(cols, key="SD"),
                sg.Checkbox("generate", key="GEN", default=True),
            ],
            [sg.Text("BSR", s=txt), sg.DropDown(cols, key="BSR", default_value="BSR")],
            [
                sg.Text("Price", s=txt),
                sg.DropDown(cols, key="PRICE", default_value="Price $"),
                sg.Checkbox("EUR?", key="CURR"),
            ],
            [
                sg.Button("OK", change_submits=True),
                sg.Button("Back", change_submits=True, key="BACK"),
            ],
        ],
    ).read(close=True)
    if d_cols["GEN"] == True:
        f[d_cols["SM"]] = f[d_cols["SM"]].astype(float)
        f["Sales daily"] = round(f[d_cols["SM"]] / 30, 2)
        d_cols["SD"] = "Sales daily"
    del d_cols["GEN"]
    # if d_cols['CURR'] == True:
    currency = d_cols["PRICE"]
    del d_cols["CURR"]
    if event == "BACK":
        stop = True
        return f, d_cols, cols, stop
    else:
        stop = False
        d_cols = list(d_cols.values())
        while "" in d_cols:
            d_cols.remove("")

        f[d_cols] = f[d_cols].applymap(
            lambda x: str(x)
            .replace('"', "")
            .replace(" ", "")
            .replace("\xa0", "")
            .replace(",", "")
        )
        f[d_cols] = f[d_cols].astype(float)
        return f, d_cols, cols, stop, currency


def create_index_cols(cols):
    event, i_cols = sg.Window(
        "Select index (aggregation) columns",
        layout=[
            [sg.Text("Parameter 1", s=txt), sg.DropDown(cols)],
            [sg.Text("Parameter 2", s=txt), sg.DropDown(cols)],
            [sg.Text("Parameter 3", s=txt), sg.DropDown(cols)],
            [sg.Text("Parameter 4", s=txt), sg.DropDown(cols)],
            [
                sg.Button("OK", change_submits=True),
                sg.Button("Back", change_submits=True, key="BACK"),
            ],
        ],
    ).read(close=True)
    if event == "BACK":
        stop = True
        return i_cols, stop
    else:
        stop = False
        i_cols = list(i_cols.values())
        if "" not in i_cols:
            i_cols.append("")
        return i_cols, stop


def pivot_create(f, i_cols, d_cols):
    while "" in i_cols:
        i_cols.remove("")

    i_cols += ["Price range"]

    price_bins = [
        0,
        2,
        3,
        5,
        10,
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        60,
        70,
        80,
        90,
        100,
        120,
        150,
        200,
        250,
        300,
        350,
        400,
        500,
    ]
    variation_bins = [0, 2, 5, 10, 20, 50, 100, 150, 200, 300, 400, 500]
    contribution_bins = [0, 20, 30, 50, 80, 100]
    f["Price range"] = pd.cut(f[d_cols[-1]], price_bins)

    # count number of variations per each listing
    # and count how many top variations contribute to 80% of sales
    variation_counts = f.pivot_table(
        values=["ASIN", "Sales"],
        index=["Brand", "Total Sales"],
        aggfunc={
            "ASIN": lambda x: len(x.unique()),
            "Sales": lambda x: x.sort_values(ascending=False)
            .cumsum()
            .le(x.sum() * 0.8)
            .sum()
            + 1,
            # 'Total Sales': lambda x: x.sort_values(ascending = False).cumsum().lt(x.sum()*.8).sum() if x.sort_values(ascending = False).cumsum().lt(x.sum()*.8).sum() != 0 else len(x.unique())
        },
    ).reset_index()
    variation_counts.rename(
        columns={"ASIN": "Variation count", "Sales": "Contributing variations"},
        inplace=True,
    )

    f = pd.merge(f, variation_counts, how="left", on=["Brand", "Total Sales"])

    f["# of variations"] = pd.cut(f["Variation count"], variation_bins)
    f["% of contributing variations"] = pd.cut(
        round(f["Contributing variations"] / f["Variation count"] * 100, 0),
        contribution_bins,
    )
    result = f.copy()

    result = result.sort_values(
        ["Total Sales", "Brand", "Sales daily"], ascending=[False, True, False]
    )
    result["Listing share"] = round(
        result["Total Sales"] / result["Sales"].sum() * 100, 1
    )

    pivot = result[d_cols + i_cols].copy()
    pivot[i_cols] = pivot[i_cols].applymap(
        lambda x: str(x).replace('"', "").replace("'", "").strip()
    )
    means = pivot.pivot_table(d_cols, index=i_cols, aggfunc="mean").reset_index()
    means.rename(columns={"Sales": "Avg sales per variation, monthly"}, inplace=True)
    sums = pivot.pivot_table("Sales", index=i_cols, aggfunc="sum").reset_index()
    sums.rename(columns={"Sales": "Sales sum"}, inplace=True)
    pivot = pd.merge(means, sums, how="left", on=i_cols)
    pivot["Sales share"] = round(
        (pivot["Sales sum"] / pivot["Sales sum"].sum()) * 100, 1
    )

    i_cols += ["# of variations", "% of contributing variations"]
    pivot2 = result[d_cols + i_cols].copy()
    pivot2[i_cols] = pivot2[i_cols].applymap(
        lambda x: str(x).replace('"', "").replace("'", "").strip()
    )
    means = pivot2.pivot_table(d_cols, index=i_cols, aggfunc="mean").reset_index()
    means.rename(columns={"Sales": "Avg sales per variation, monthly"}, inplace=True)
    sums = pivot2.pivot_table("Sales", index=i_cols, aggfunc="sum").reset_index()
    sums.rename(columns={"Sales": "Sales sum"}, inplace=True)
    pivot2 = pd.merge(means, sums, how="left", on=i_cols)
    pivot2["Sales share"] = round(
        (pivot2["Sales sum"] / pivot2["Sales sum"].sum()) * 100, 1
    )

    d_cols += ["Sales share", "Sales sum"]
    d_cols.remove("Sales")
    pivot[d_cols] = round(pivot[d_cols], 2)
    pivot2[d_cols] = round(pivot2[d_cols], 2)
    return pivot, pivot2, result


def plot_preview(f, i_cols, d_cols, pivot):
    i_cols += [""]
    # plot_size = (800,400)
    btn_col = [
        [
            sg.Text("x axis", size=txt2),
            sg.DropDown(i_cols, default_value=d_cols[-1], change_submits=True, key="X"),
        ],
        [
            sg.Text("y axis", size=txt2),
            sg.DropDown(i_cols, default_value=d_cols[0], change_submits=True, key="Y"),
        ],
        [
            sg.Text("Color", size=txt2),
            sg.DropDown(i_cols, default_value=None, change_submits=True, key="COLOR"),
        ],
        [
            sg.Text("Size", size=txt2),
            sg.DropDown(i_cols, default_value=None, change_submits=True, key="SIZE"),
        ],
        [
            sg.Text("Style", size=txt2),
            sg.DropDown(i_cols, default_value=None, change_submits=True, key="STYLE"),
        ],
        [
            sg.Text("Columns", size=txt2),
            sg.DropDown(i_cols, default_value=None, change_submits=True, key="COLS"),
        ],
    ]
    plot_image = sg.Image(
        source=os.path.join(prefix, r"70 Data & Technology\70.03 Scripts\mellanni.png")
    )  # , size = plot_size)
    plot2_image = sg.Image(
        source=os.path.join(prefix, r"70 Data & Technology\70.03 Scripts\mellanni.png")
    )  # , size = plot_size)
    img_col = [[plot_image], [plot2_image]]

    layout = [
        [
            sg.Column(btn_col),
            sg.Column(img_col),
        ],  # , scrollable = True, size = (plot_size[0],plot_size[1]*2))],
        [sg.Button("OK", change_submits=True)],
    ]
    window = sg.Window(
        "Select the plot layout", layout, size=(1000, 700), resizable=True
    )
    while True:
        event, values = window.read()

        if (
            event == sg.WIN_CLOSED or event == "Cancel"
        ):  # if user closes window or clicks cancel
            break
        elif any(
            [
                event == "COLOR",
                event == "SIZE",
                event == "STYLE",
                event == "COLS",
                event == "X",
                event == "Y",
            ]
        ):
            x, y, hue, size, style, col = (
                values["X"],
                values["Y"],
                values["COLOR"],
                values["SIZE"],
                values["STYLE"],
                values["COLS"],
            )
            plot_cols = relplot_cols(x, y, hue, size, style, col)
            plot_temp(plot_cols, f, pivot)
            plot_image.update(source="plot.png")  # , size = plot_size)
            plot2_image.update(source="plot2.png")  # , size = plot_size)
        elif event == "OK":
            break
    window.close()
    return None


def main_func():
    # read the file
    f = read_file()
    if f is None:
        return None
    # get data columns
    f, d_cols, cols, stop, currency = create_data_cols(f)
    if stop == False:
        # get index columns
        i_cols, stop = create_index_cols(cols)
    else:
        main_func()
        return None
    if stop == False:
        pivot, pivot2, result = pivot_create(f, i_cols, d_cols)
        pivot = pivot.sort_values("Sales sum", ascending=False)
        pivot2 = pivot2.sort_values("Sales sum", ascending=False)
        # plot_preview(f,i_cols, d_cols, pivot)
        plot_temp([currency, "Variation count", "Sales"], result)
        output = None
        while output == None or output == "":
            output = sg.PopupGetFolder("Output?")
        try:
            with pd.ExcelWriter(os.path.join(output, "result.xlsx")) as writer:
                pivot.to_excel(writer, sheet_name="Price bins", index=False)
                workbook = writer.book
                worksheet = writer.sheets["Price bins"]
                worksheet.insert_image("K2", "plot.png")
                # worksheet.insert_image('K30', 'plot2.png')
                pivot2.to_excel(writer, sheet_name="Expanded", index=False)
                mm.format_header(pivot2, writer, "Expanded")
                result.to_excel(writer, sheet_name="Refined", index=False)
                mm.format_header(result, writer, "Refined")
                os.startfile(output)
        except:
            sg.Popup("File is open")
    else:
        main_func()
        return None

    while "plot.png" in os.listdir(os.getcwd()) or "plot2.png" in os.listdir(
        os.getcwd()
    ):
        try:
            os.remove("plot.png")
            os.remove("plot2.png")
        except:
            pass
    return None


if __name__ == "__main__":
    main_func()
