"""The pet game. Hardware-agnostic: no board, busio or pygame imports in here.

state.py    stats, decay, needs, sleep, attention (no displayio either; unit-tested)
input.py    A cycles the icon cursor, B selects, C cancels
sprites.py  placeholder 1-bit art as text rows
ui.py       displayio groups for the 240x240 square
game.py     Game.update(now, events): the one entry point code.py and the sim call
"""
