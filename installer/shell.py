"""The furniture: the header, the hairline, labels and the body column."""

from __future__ import annotations

import pathlib

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from installer import theme
from installer.wording import PRODUCT, TAGLINE

TITLE_GAP_PX = 2


def pane(parent: QWidget | None = None) -> QWidget:
    """A container, said to be no focus stop rather than assumed to be one."""
    holder = QWidget(parent)
    holder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return holder


def rule(parent: QWidget) -> QFrame:
    """The hairline between the bands."""
    line = QFrame(parent)
    line.setObjectName("Rule")
    line.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    line.setFrameShape(QFrame.Shape.NoFrame)
    line.setFixedHeight(1)
    return line


def label(parent: QWidget, text: str, name: str = "") -> QLabel:
    """A piece of text, wrapped, taking no focus."""
    made = QLabel(text, parent)
    if name:
        made.setObjectName(name)
    made.setWordWrap(True)
    made.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return made


def option(parent: QWidget, text: str, checked: bool) -> QCheckBox:
    """One choice, opening on what is already true."""
    box = QCheckBox(text, parent)
    box.setChecked(checked)
    box.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    return box


def header(
    parent: QWidget, mark: pathlib.Path | None, controls: tuple[QPushButton, ...]
) -> QWidget:
    """The mark, then the name over its tagline with the controls at the right.

    The tagline belongs to the header rather than to the title, so it is given
    the whole width beside the mark rather than the width of the name above it.
    Confined to the name it broke early and stranded its last word, with the
    room it needed sitting unused beside the controls.

    No version here: it has no baseline to sit on beside a 32px title and reads
    as a fragment come adrift. It belongs in the body, in the sentence naming
    what is installed and what setup carries.
    """
    band = pane(parent)
    row = QHBoxLayout(band)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(theme.HEADER_GAP_PX)

    if mark is not None:
        badge = QLabel(band)
        badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        badge.setPixmap(
            QPixmap(str(mark)).scaled(
                theme.MARK_PX,
                theme.MARK_PX,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        row.addWidget(badge)

    names = pane(band)
    column = QVBoxLayout(names)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(TITLE_GAP_PX)

    title = label(names, PRODUCT, "Title")
    title.setWordWrap(False)
    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(theme.HEADER_GAP_PX)
    top.addWidget(title)
    top.addStretch()
    for control in controls:
        top.addWidget(control, 0, Qt.AlignmentFlag.AlignTop)
    column.addLayout(top)
    column.addWidget(label(names, TAGLINE, "Tagline"))

    row.addWidget(names, 1)
    return band
