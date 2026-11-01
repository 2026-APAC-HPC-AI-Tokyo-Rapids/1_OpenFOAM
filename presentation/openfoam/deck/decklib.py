"""Helpers on top of python-pptx that add text, cards, tables and charts in the team deck's own style.

Fonts follow the template (Meiryo everywhere); colours come from palette.py. The words Baseline, Basic and Bonus take their
tier colour wherever they appear in normal text and in titles, so the colours need no legend. Positions and sizes are in
inches.
"""

import copy
import io
import re

from lxml import etree
from PIL import Image
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from palette import BASE, BASIC, BONUS, GRID, INK, LIGHT, LINE, MUTED, NAVY, WHITE

FONT = "メイリオ"
NO_GRID_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ALIGN = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}
ANCHOR = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}
LABEL_POSITION = {"outEnd": XL_LABEL_POSITION.OUTSIDE_END, "inEnd": XL_LABEL_POSITION.INSIDE_END, "inBase": XL_LABEL_POSITION.INSIDE_BASE, "ctr": XL_LABEL_POSITION.CENTER}


def rgb(hex_):
    return RGBColor.from_string(hex_)


# ---------------------------------------------------------------- text
NBSP = " "
NBHYPHEN = "‑"
_PERCENT = re.compile(r"(\d) %")
_UNIT = re.compile(r"(\d) (GB/s|Gb/s|TFLOP/s|GB|TB|MB|MiB|M|s/step|s|µs|ms|nodes?|cores?|channels?|jobs?|controls?|ranks?|steps?|runs?|sockets?|domains?|files|lines|calls|threads|L3s)(?=[^\w/]|$)")
_CHAIN = re.compile(r"([\d%]) (/|→|to|v) (?=[\d−+])")
_COMPOUND = re.compile(r"\b(bit|case|pre|fixed|run|node|re|off|non|two|same)-(?=[a-z])|\b(\d+)-(?=(?:node|core|step|byte)s?\b)")
_PAIRS = re.compile(r"\b(max|slowest|r|R²) (/|=) (?=[\w+−])")
TIER_COLOURS = {"baseline": BASE, "basic": BASIC, "bonus": BONUS}
# "pre-change baseline" and "its own baseline" (the Bonus build without its patches), "the new baseline", and the organisers'
# "common baseline" are not our Baseline configuration
_TIER = re.compile(r"(?<!change )(?<!its own )(?<!new )(?<!common )(?<!Common )\b(baseline|Baseline|BASELINE|Basic|BASIC|Bonus|BONUS)\b")


def tidy(text):
    """Keep numbers with their units, short number chains (1 / 2 / 4, 3.65 → 2.90, 3 v 3, −1% to +6%) and short compounds on one line.

    % is not a unit: "21 %" is written "21%". Code-like tokens (--cpu-bind, PrgEnv-gnu) keep a plain hyphen so that they can
    be copied from the slide. PowerPoint still breaks after an en dash (3.19–3.58) whatever joiner follows it; write
    "3.19 to 3.58" where that matters. A joined token wider than its box is broken anywhere, so give table columns room for
    "−1.54%" or "2 nodes".
    """
    text = _PERCENT.sub(r"\1%", text)
    text = _COMPOUND.sub(lambda m: (m.group(1) or m.group(2)) + NBHYPHEN, text)
    text = _UNIT.sub(lambda m: m.group(1) + NBSP + m.group(2), text)
    text = _PAIRS.sub(lambda m: m.group(1) + NBSP + m.group(2) + NBSP, text)
    previous = None
    while previous != text:
        previous = text
        text = _CHAIN.sub(lambda m: m.group(1) + NBSP + m.group(2) + NBSP, text)
    return text.replace("≈ ", "≈" + NBSP)


def tier_runs(text, color):
    """Split text so that Baseline, Basic and Bonus take their tier colour; text in white, red or a tier colour stays as it is.

    color None stands for an inherited colour (titles). Returns [(piece, colour or None), ...].
    """
    if color not in (None, INK, MUTED, NAVY):
        return [(text, color)]
    return [(piece, TIER_COLOURS[piece.lower()] if k % 2 else color) for k, piece in enumerate(_TIER.split(text)) if piece]


def style_run(run, size=None, bold=None, italic=None, color=None, font=FONT):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color is not None:
        f.color.rgb = rgb(color)
    f.name = font
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", font)


def _bullet_position(pPr):
    position = 0
    for i, child in enumerate(pPr):
        if child.tag in (qn("a:lnSpc"), qn("a:spcBef"), qn("a:spcAft")):
            position = i + 1
    return position


def set_bullet(p, char="●", color=NAVY, size_pct=60, indent=0.24, font=FONT, number=False):
    """A bullet, or with number=True an automatic number (1. 2. 3.) in the bullet's place."""
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(indent))))
    for tag in ("a:buClr", "a:buSzPct", "a:buFont", "a:buChar", "a:buAutoNum", "a:buNone", "a:buClrTx", "a:buSzTx", "a:buFontTx"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    clr = etree.Element(qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", color)
    size = etree.Element(qn("a:buSzPct"))
    size.set("val", str(int(size_pct * 1000)))
    typeface = etree.Element(qn("a:buFont"))
    typeface.set("typeface", font)
    if number:
        bullet = etree.Element(qn("a:buAutoNum"))
        bullet.set("type", "arabicPeriod")
    else:
        bullet = etree.Element(qn("a:buChar"))
        bullet.set("char", char)
    position = _bullet_position(pPr)
    for k, el in enumerate((clr, size, typeface, bullet)):
        pPr.insert(position + k, el)


def fill_paragraph(p, para, size=16, color=INK, bold=False, align="l", line=None, space_after=0, space_before=0, bullet=None):
    """A paragraph is a str, a (text, options) run, a list of runs, or a dict with "runs" plus paragraph options.

    Run options: b, i, color, size. A run whose text is "\\n" is a line break.
    """
    options = {}
    if isinstance(para, dict):
        options = para
        runs = para["runs"]
    elif isinstance(para, (str, tuple)):
        runs = [para]
    else:
        runs = para
    p.alignment = ALIGN[options.get("align", align)]
    if options.get("line", line):
        p.line_spacing = options.get("line", line)
    if options.get("space_before", space_before):
        p.space_before = Pt(options.get("space_before", space_before))
    if options.get("space_after", space_after):
        p.space_after = Pt(options.get("space_after", space_after))
    for run in runs:
        text, run_options = (run, {}) if isinstance(run, str) else run
        if text == "\n":
            p.add_line_break()
            continue
        for piece, piece_color in tier_runs(tidy(text), run_options.get("color", options.get("color", color))):
            r = p.add_run()
            r.text = piece
            style_run(r, size=run_options.get("size", options.get("size", size)), bold=run_options.get("b", options.get("bold", bold)), italic=run_options.get("i"), color=piece_color)
    b = options.get("bullet", bullet)
    if b:
        set_bullet(p, **(b if isinstance(b, dict) else {}))


def add_text(slide, x, y, w, h, paras, size=16, color=INK, bold=True, align="l", anchor="t", margin=(0, 0, 0, 0), line=None, space_after=0, space_before=0, bullet=None, name=None):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shape.name = name
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (Inches(m) for m in margin)
    tf.vertical_anchor = ANCHOR[anchor]
    if isinstance(paras, (str, tuple, dict)):
        paras = [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        fill_paragraph(p, para, size, color, bold, align, line, space_after, space_before, bullet)
    return shape


def bullets(slide, x, y, w, h, items, size=13, color=INK, space_after=6, anchor="t", line=None):
    return add_text(slide, x, y, w, h, [{"runs": item if isinstance(item, list) else [item], "bullet": True, "space_after": space_after} for item in items], size=size, color=color, anchor=anchor, line=line)


# ---------------------------------------------------------------- shapes
def box(slide, x, y, w, h, fill=LIGHT, line=None, line_w=0.75, radius=0.05, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    if fill:
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(fill)
    else:
        sh.fill.background()
    if line:
        sh.line.color.rgb = rgb(line)
        sh.line.width = Pt(line_w)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    if name:
        sh.name = name
    return sh


def shape_text(sh, paras, size=14, color=WHITE, bold=True, align="c", anchor="m", margin=(0.02, 0.02, 0.02, 0.02)):
    tf = sh.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (Inches(m) for m in margin)
    tf.vertical_anchor = ANCHOR[anchor]
    if isinstance(paras, (str, tuple, dict)):
        paras = [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        fill_paragraph(p, para, size, color, bold, align)


def circle_num(slide, x, y, d, text, fill=NAVY, size=14):
    sh = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    shape_text(sh, text, size=size, margin=(0, 0, 0, 0))
    return sh


def arrow_line(slide, x1, y1, x2, y2, color=NAVY, width=1.5, head=True):
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    connector.line.color.rgb = rgb(color)
    connector.line.width = Pt(width)
    if head:
        tail = etree.SubElement(connector.line._get_or_add_ln(), qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    return connector


def block_arrow(slide, x, y, w, h, color=NAVY):
    return box(slide, x, y, w, h, fill=color, shape=MSO_SHAPE.RIGHT_ARROW)


# ---------------------------------------------------------------- pictures
def _open(src):
    if isinstance(src, (bytes, bytearray)):
        return io.BytesIO(src), Image.open(io.BytesIO(src))
    return str(src), Image.open(src)


def picture(slide, src, x, y, w=None, h=None, crop=(0, 0, 0, 0), name=None):
    """Add a picture; give w or h and the other follows the visible (cropped) aspect ratio."""
    stream, image = _open(src)
    width, height = image.size
    left, top, right, bottom = crop
    aspect = (width * (1 - left - right)) / (height * (1 - top - bottom))
    w = h * aspect if w is None else w
    h = w / aspect if h is None else h
    pic = slide.shapes.add_picture(stream, Inches(x), Inches(y), Inches(w), Inches(h))
    pic.crop_left, pic.crop_top, pic.crop_right, pic.crop_bottom = crop
    if name:
        pic.name = name
    return pic


def picture_fit(slide, src, x, y, w, h, crop=(0, 0, 0, 0), halign="c", valign="t", name=None):
    _, image = _open(src)
    width, height = image.size
    left, top, right, bottom = crop
    aspect = (width * (1 - left - right)) / (height * (1 - top - bottom))
    pw, ph = (h * aspect, h) if w / h > aspect else (w, w / aspect)
    px = x + {"l": 0, "c": (w - pw) / 2, "r": w - pw}[halign]
    py = y + {"t": 0, "m": (h - ph) / 2, "b": h - ph}[valign]
    return picture(slide, src, px, py, pw, ph, crop, name)


# ---------------------------------------------------------------- tables
def cell_border(cell, side="b", color=LINE, width=0.75, none=False):
    tcPr = cell._tc.get_or_add_tcPr()
    order = ["a:lnL", "a:lnR", "a:lnT", "a:lnB"]
    tag = {"l": "a:lnL", "r": "a:lnR", "t": "a:lnT", "b": "a:lnB"}[side]
    for el in tcPr.findall(qn(tag)):
        tcPr.remove(el)
    ln = etree.Element(qn(tag))
    if none:
        ln.set("w", "0")
        etree.SubElement(ln, qn("a:noFill"))
    else:
        ln.set("w", str(int(Pt(width))))
        ln.set("cap", "flat")
        ln.set("cmpd", "sng")
        ln.set("algn", "ctr")
        etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr")).set("val", color)
        etree.SubElement(ln, qn("a:prstDash")).set("val", "solid")
    before = [qn(o) for o in order[: order.index(tag)]]
    position = 0
    for k, child in enumerate(tcPr):
        if child.tag in before:
            position = k + 1
    tcPr.insert(position, ln)


def table(slide, x, y, col_w, rows, row_h=0.42, size=14, header=True, header_fill=WHITE, header_color=NAVY, header_rule=NAVY, zebra=False, aligns=None, fills=None, colors=None, bolds=None, bold=True, margins=(0.09, 0.06, 0.09, 0.06), valign="m", name=None, color=INK, row_heights=None):
    """rows[i][j] is a cell: a str, or a list of paragraphs (see fill_paragraph). fills, colors and bolds are per-cell overrides.

    By default a table has horizontal rules only: a bold navy header over a navy rule, and thin rules between the rows. Every
    cell is bold unless bold=False or bolds says otherwise.
    """
    nr, nc = len(rows), len(col_w)
    frame = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(sum(col_w)), Inches(row_h * nr))
    if name:
        frame.name = name
    tbl = frame.table
    tblPr = tbl._tbl.tblPr
    style = tblPr.find(qn("a:tableStyleId"))
    if style is None:
        style = etree.SubElement(tblPr, qn("a:tableStyleId"))
    style.text = NO_GRID_STYLE
    tblPr.set("firstRow", "1" if header else "0")
    tblPr.set("bandRow", "0")
    for j, width in enumerate(col_w):
        tbl.columns[j].width = Inches(width)
    for i in range(nr):
        tbl.rows[i].height = Inches(row_heights[i] if row_heights else row_h)
    for i, row in enumerate(rows):
        head = header and i == 0
        for j in range(nc):
            cell = tbl.cell(i, j)
            if head:
                fill = header_fill
            elif fills and fills[i] and fills[i][j]:
                fill = fills[i][j]
            else:
                fill = LIGHT if zebra and i % 2 == 0 else WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(fill)
            cell.margin_left, cell.margin_top, cell.margin_right, cell.margin_bottom = (Inches(m) for m in margins)
            cell.vertical_anchor = ANCHOR[valign]
            tf = cell.text_frame
            tf.word_wrap = True
            cell_color = header_color if head else (colors[i][j] if colors and colors[i] and colors[i][j] else color)
            cell_bold = True if head else (bolds[i][j] if bolds and bolds[i] and bolds[i][j] is not None else bold)
            value = row[j] if j < len(row) else ""
            for k, para in enumerate(value if isinstance(value, list) else [value]):
                p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                fill_paragraph(p, para, size=size, color=cell_color, bold=cell_bold, align=aligns[j] if aligns else "l")
            for side in ("l", "r", "t"):
                cell_border(cell, side, none=True)
            cell_border(cell, "b", color=header_rule if head else LINE, width=1.25 if head else 0.75)
    return frame


# ---------------------------------------------------------------- charts
def _chart_frame_off(chart):
    space = chart._chartSpace
    for el in space.findall(qn("c:spPr")):
        space.remove(el)
    spPr = etree.Element(qn("c:spPr"))
    etree.SubElement(spPr, qn("a:noFill"))
    etree.SubElement(etree.SubElement(spPr, qn("a:ln")), qn("a:noFill"))
    space.find(qn("c:chart")).addnext(spPr)


def _axis_text(axis, size, color):
    axis.tick_labels.font.size = Pt(size)
    axis.tick_labels.font.color.rgb = rgb(color)
    axis.tick_labels.font.name = FONT


def bar_chart(slide, x, y, w, h, categories, series, colors=None, point_colors=None, horizontal=True, stacked=False, number_format="0.00", label_format=None, vmin=None, vmax=None, major=None, font_size=13, label_size=14, gap=55, overlap=None, legend=False, value_axis=True, gridlines=True, label_pos="outEnd", labelled=None, label_color=INK, cat_size=None, name=None):
    """A clustered or stacked bar/column chart with data labels; series is [(name, values), ...].

    labelled lists the series indexes that get data labels (all by default). label_format, the labels' number format, may
    hold a condition such as [<1]"" that hides small values; number_format goes into the chart's XML as it is, so it may not.
    """
    data = CategoryChartData(number_format=number_format)
    data.categories = categories
    for series_name, values in series:
        data.add_series(series_name, values)
    if horizontal:
        kind = XL_CHART_TYPE.BAR_STACKED if stacked else XL_CHART_TYPE.BAR_CLUSTERED
    else:
        kind = XL_CHART_TYPE.COLUMN_STACKED if stacked else XL_CHART_TYPE.COLUMN_CLUSTERED
    frame = slide.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data)
    if name:
        frame.name = name
    chart = frame.chart
    chart.has_title = False
    chart.font.name = FONT
    chart.font.size = Pt(font_size)
    chart.font.bold = True
    chart.font.color.rgb = rgb(INK)
    _chart_frame_off(chart)
    plot = chart.plots[0]
    plot.gap_width = gap
    if overlap is not None:
        plot.overlap = overlap
    plot.vary_by_categories = False
    for si, ser in enumerate(plot.series):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(colors[si] if colors else NAVY)
        ser.format.line.fill.background()
        ser.invert_if_negative = False
        if point_colors and si == 0:
            for pi, point_color in enumerate(point_colors):
                point = ser.points[pi]
                point.format.fill.solid()
                point.format.fill.fore_color.rgb = rgb(point_color)
                point.format.line.fill.background()
            # a c:dPt without its own invertIfNegative is drawn inverted (white) when the value is negative
            for dPt in ser._element.findall(qn("c:dPt")):
                if dPt.find(qn("c:invertIfNegative")) is None:
                    invert = etree.Element(qn("c:invertIfNegative"))
                    invert.set("val", "0")
                    dPt.find(qn("c:idx")).addnext(invert)
        if labelled is None or si in labelled:
            labels = ser.data_labels
            labels.show_value = True
            labels.number_format = label_format or number_format
            labels.number_format_is_linked = False
            labels.position = LABEL_POSITION[label_pos]
            labels.font.size = Pt(label_size)
            labels.font.bold = True
            labels.font.name = FONT
            labels.font.color.rgb = rgb(label_color)
    value = chart.value_axis
    value.has_major_gridlines = gridlines
    if gridlines:
        value.major_gridlines.format.line.color.rgb = rgb(GRID)
        value.major_gridlines.format.line.width = Pt(0.75)
    value.format.line.fill.background()
    value.major_tick_mark = XL_TICK_MARK.NONE
    value.minor_tick_mark = XL_TICK_MARK.NONE
    _axis_text(value, font_size - 1, INK)
    if vmin is not None:
        value.minimum_scale = vmin
    if vmax is not None:
        value.maximum_scale = vmax
    if major is not None:
        value.major_unit = major
    value.visible = value_axis
    category = chart.category_axis
    category.format.line.color.rgb = rgb("B8C2D3")
    category.major_tick_mark = XL_TICK_MARK.NONE
    category.minor_tick_mark = XL_TICK_MARK.NONE
    _axis_text(category, cat_size or font_size, INK)
    category.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP if legend is True else legend
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(font_size)
        chart.legend.font.name = FONT
    return frame


# ---------------------------------------------------------------- slide plumbing
def shape_info(el):
    """(name, placeholder type) of a spTree child; the type is None for shapes that are not placeholders."""
    cnv = el.find(".//" + qn("p:cNvPr"))
    ph = el.find(".//" + qn("p:ph"))
    return (cnv.get("name") if cnv is not None else ""), (ph.get("type", "obj") if ph is not None else None)


def prune_rels(slide):
    """Drop the slide's relationships that its XML no longer refers to (r:id, r:embed, r:link, ...)."""
    used = set()
    for el in slide.part._element.iter():
        for key, value in el.attrib.items():
            if key.startswith(f"{{{R_NS}}}"):
                used.add(value)
    for rId in list(slide.part.rels.keys()):
        if slide.part.rels[rId].reltype.endswith(("/slideLayout", "/notesSlide")):
            continue
        if rId not in used:
            slide.part.rels.pop(rId)


def clear_slide(slide, keep=()):
    """Remove every shape except the title, the slide number and the shapes named in keep."""
    tree = slide.shapes._spTree
    for el in list(tree):
        if etree.QName(el).localname in ("nvGrpSpPr", "grpSpPr", "extLst"):
            continue
        name, ph = shape_info(el)
        if ph in ("title", "sldNum") or name in keep:
            continue
        tree.remove(el)
    prune_rels(slide)


def remove_body_placeholders(slide):
    tree = slide.shapes._spTree
    for el in list(tree):
        if shape_info(el)[1] not in (None, "title", "sldNum"):
            tree.remove(el)


def add_sldnum(slide, template_sp):
    """Copy the template's slide-number field onto the slide (layout placeholders do not bring it along)."""
    tree = slide.shapes._spTree
    for el in list(tree):
        if shape_info(el)[1] == "sldNum":
            tree.remove(el)
    sp = copy.deepcopy(template_sp)
    cnv = sp.find(".//" + qn("p:cNvPr"))
    for ext in cnv.findall(qn("a:extLst")):
        cnv.remove(ext)
    ids = [int(e.get("id")) for e in slide._element.iter(qn("p:cNvPr")) if e.get("id", "").isdigit()]
    cnv.set("id", str(max(ids + [1]) + 1))
    tree.append(sp)


def set_title(slide, text):
    """Replace the title text and drop any shrink-to-fit scale, so every title uses the master's 32 pt; tier words take their colour."""
    tf = slide.shapes.title.text_frame
    body = tf._txBody.bodyPr
    for el in list(body):
        body.remove(el)
    tf.text = ""
    p = tf.paragraphs[0]
    for piece, color in tier_runs(text, None):
        r = p.add_run()
        r.text = piece
        r._r.get_or_add_rPr().set("lang", "en-US")
        if color:
            r.font.color.rgb = rgb(color)


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text.strip("\n")
