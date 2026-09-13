import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('detector',Path(__file__).with_name('focus-detector.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
d=m.FocusDetector('user-a');assert not d.register('agent');assert not d.observe('user-b');assert d.observe('agent');assert not d.observe('agent');assert not d.observe('user-a');assert d.observe('agent')
d=m.FocusDetector('user-a');assert not d.observe('popup');assert d.register('popup');assert not d.register('popup')
d=m.FocusDetector('user-a');assert not d.observe('');assert not d.observe('user-c')
print('User switches, agent transfers, duplicate observations, and active-before-map ordering passed')
