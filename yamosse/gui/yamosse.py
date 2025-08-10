import tkinter as tk
from tkinter import ttk
import webbrowser
from os import fsencode as fsenc

import yamosse.output as yamosse_output

from .. import gui
from . import sorted as gui_sorted
from . import calibrate as gui_calibrate

RESIZABLE = True
SIZE = (600, 585)

UNIT_CLASSES = 'classes'
UNIT_SECONDS = 'seconds'

TIP_WEIGHTS = ('The weights file for the YAMNet model. This option will be disabled if you are '
  'using the TensorFlow Hub release of YAMNet.')

TIP_TIMESPAN = ('If a sound is less than this length in seconds, it will be combined into one '
  'timestamp. Otherwise, it will be output as a timespan: two timestamps with a dash inbetween. '
  'To never use timespans, set this to zero.')

TIP_TIMESPAN_SPAN_ALL = ('If checked, timestamps are not used. Instead, one prediction is made, '
  'spanning the entire sound file.')

TIP_BACKGROUND_NOISE_VOLUME = ('The volume below which all sounds are ignored. Setting this to '
  'at least 1% will make scans significantly faster during silent parts of the sound file. Set '
  'this to 0% to scan everything.')

TIP_BACKGROUND_NOISE_VOLUME_LOG = ('Logarithmic volume scale (with a 60 dB range.) This is the '
  'volume scale you should use in most cases.')

TIP_BACKGROUND_NOISE_VOLUME_LINEAR = 'Linear volume scale.'

TIP_OUTPUT_FILE_OPTIONS_SORT_BY = ('Whether to sort results by the number of sounds identified, '
  'or alphabetically by file name.')

TIP_OUTPUT_FILE_OPTIONS_SORT_REVERSE = 'If checked, results will be sorted in reverse.'

TIP_OUTPUT_FILE_OPTIONS_ITEM_DELIMITER = ('Separator inbetween each timestamp or class. Escape '
  'characters are supported. This option is ignored if the output is a JSON file.')

TIP_OUTPUT_FILE_OPTIONS_INDENT = 'If checked, the items will be indented.'

TIP_OUTPUT_FILE_OPTIONS_OUTPUT_OPTIONS = 'Output the options that were used for the YAMScan.'

TIP_OUTPUT_FILE_OPTIONS_OUTPUT_SCORE = ('Output the score percentage along with each timestamp, '
  'so you can see how certain the model is that it identified a sound at that timestamp.')

TIP_WORKER_OPTIONS_MEMORY_LIMIT = ('The TensorFlow logical device memory limit, in megabytes. It '
  'will be multiplied by the number of workers and the number of GPUs. This option is ignored if '
  'GPU Acceleration is disabled. Errors may occur if it is too high or low.')

TIP_WORKER_OPTIONS_MAX_WORKERS = ('Increasing the max number of workers will make scans faster, '
  'unless it is set too high - then you might run out of memory (workers cost memory, though '
  'lowering the memory limit will make them cost less.)')

TIP_WORKER_OPTIONS_HIGH_PRIORITY = ('Mark YAMosse as High Priority to make scans faster, at the '
  'expense of other programs running slower.')

URL_ONLINE_HELP = 'https://github.com/tomysshadow/YAMosse/blob/main/README.md'


def make_header(frame, title):
  ttk.Label(frame, text=title, style='Title.TLabel').grid()


def make_input(frame, variables, filetypes):
  buttons_frame = gui.make_filedialog(
    frame,
    textvariable=variables['input'],
    asks=('directory', 'openfilenames'),
    parent=frame.winfo_toplevel(),
    filetypes=filetypes
  )[2][0]
  
  recursive_checkbutton = ttk.Checkbutton(buttons_frame,
    text='Recursive', variable=variables['input_recursive'])
  
  recursive_checkbutton.pack(side=tk.RIGHT)
  recursive_checkbutton.lower() # fix tab order


def make_classes(frame, variables, class_names):
  treeview_widgets = gui.make_treeview(
    frame,
    columns=gui.heading_text_treeview_columns(('#', 'Class Names')),
    items=gui.values_treeview_items(enumerate(class_names, start=1)),
    show='headings',
    selectmode=tk.EXTENDED
  )
  
  treeview = treeview_widgets[1][0]
  
  # load and dump the classes variable to and from the treeview
  # classes isn't guaranteed to be sorted (it usually doesn't matter)
  # we sort it just to get the first class for display purposes
  classes_variable = variables['classes']
  treeview.selection_set(classes_variable)
  if classes_variable: treeview.see(sorted(classes_variable)[0])
  
  def select_treeview(e):
    variables['classes'] = [int(s) for s in e.widget.selection()]
  
  treeview.bind('<<TreeviewSelect>>', select_treeview)
  gui_sorted.treeview_sorted(treeview)
  gui.configure_widths_treeview(treeview, {0: 3})
  
  buttons_frame = treeview_widgets[2][0]
  
  calibrate_button = ttk.Button(
    buttons_frame,
    text='Calibrate...',
    
    command=lambda: gui.gui(
      gui_calibrate.make_calibrate,
      variables,
      class_names,
      child=True
    )
  )
  
  calibrate_button.pack(side=tk.LEFT)
  calibrate_button.lower() # fix tab order


def make_confidence_score(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  # the frame passed in sticks to NSEW
  # so that the Help Text is shown for the entire cell
  # but we want to be vertically centered
  # (only stick to EW)
  # so we create this cell frame
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make scale frame horizontally resizable
  
  scale_frame = ttk.Frame(cell_frame)
  scale_frame.grid(row=0, column=0, sticky=tk.EW)
  gui.make_scale(scale_frame, variable=variables['confidence_score'])
  
  radiobuttons_frame = ttk.Frame(cell_frame)
  radiobuttons_frame.grid(row=0, column=1, sticky=tk.E, padx=gui.PADX_QW)
  
  radiobuttons = gui.make_widgets(
    radiobuttons_frame,
    ttk.Radiobutton,
    items=gui.text_widgets_items(('Min', 'Max')),
    orient=tk.VERTICAL,
    cell=0,
    padding=gui.PADDING_Q
  )
  
  gui.link_radiobuttons(dict.fromkeys(radiobuttons),
    variables['confidence_score_minmax'])


def make_top_ranked(frame, variables, class_names):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make spinbox frame horizontally resizable
  
  spinbox_frame = ttk.Frame(cell_frame)
  spinbox_frame.grid(row=0, sticky=tk.EW)
  gui.make_spinbox(spinbox_frame, textvariable=variables['top_ranked'],
    from_=1, to=len(class_names), unit=UNIT_CLASSES)
  
  ttk.Checkbutton(cell_frame,
    text='Output Timestamps', variable=variables['top_ranked_output_timestamps']).grid(
    row=1, sticky=tk.W, pady=gui.PADY_QN)


def make_identification_options(frame, variables, class_names):
  frame.rowconfigure(0, minsize=gui.MINSIZE_ROW_RADIOBUTTONS) # make radiobuttons minimum size
  
  frame.columnconfigure((0, 1), weight=1,
    uniform='identification_options_column') # make the columns uniform
  
  confidence_score_frame = ttk.Frame(frame)
  confidence_score_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=gui.PADX_HE)
  make_confidence_score(confidence_score_frame, variables)
  
  top_ranked_frame = ttk.Frame(frame)
  top_ranked_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=gui.PADX_HW)
  make_top_ranked(top_ranked_frame, variables, class_names)
  
  radiobuttons = gui.make_widgets(
    frame,
    ttk.Radiobutton,
    items=gui.text_widgets_items(('Confidence Score', 'Top Ranked')),
    cell=0,
    sticky=tk.EW
  )
  
  gui.link_radiobuttons(
    zip(radiobuttons, (confidence_score_frame, top_ranked_frame), strict=True),
    variables['identification']
  )
  
  # fix tab order
  confidence_score_frame.lift()
  top_ranked_frame.lift()


def make_presets(frame, import_, export):
  frame.rowconfigure((0, 1), weight=1) # make buttons vertically centered
  frame.columnconfigure(0, weight=1) # one column layout
  
  import_button, export_button = gui.make_widgets(
    frame,
    ttk.Button,
    items=gui.text_widgets_items(('Import...', 'Export...')),
    orient=tk.VERTICAL,
    cell=0,
    padding=gui.PADDING_Q
  )
  
  import_button['command'] = import_
  export_button['command'] = export


def make_general(frame, variables, input_filetypes, class_names, import_preset, export_preset):
  frame.rowconfigure(1, weight=1) # make classes frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  input_labelframe = ttk.Labelframe(frame, text='Input',
    padding=gui.PADDING_HNSEW)
  
  input_labelframe.grid(row=0, sticky=tk.NSEW)
  make_input(input_labelframe, variables, input_filetypes)
  
  classes_labelframe = ttk.Labelframe(frame, text='Classes',
    padding=gui.PADDING_HNSEW)
  
  classes_labelframe.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_QN)
  make_classes(classes_labelframe, variables, class_names)
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=2, sticky=tk.NSEW, pady=gui.PADY_QN)
  
  row_frame.columnconfigure(0, weight=1) # make identification options frame horizontally resizable
  
  identification_options_labelframe = ttk.Labelframe(row_frame, text='Identification Options',
    padding=gui.PADDING_HNSEW)
  
  identification_options_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui.PADX_HE)
  make_identification_options(identification_options_labelframe, variables, class_names)
  
  presets_labelframe = ttk.Labelframe(row_frame, text='Presets',
    padding=gui.PADDING_HNSEW)
  
  presets_labelframe.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E), padx=gui.PADX_HW)
  make_presets(presets_labelframe, import_preset, export_preset)


def make_timespan(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make spinbox frame horizontally resizable
  
  spinbox_frame = ttk.Frame(cell_frame)
  spinbox_frame.grid(row=0, column=0, sticky=tk.EW)
  gui.make_spinbox(spinbox_frame, textvariable=variables['timespan'],
    from_=0, to=60, unit=UNIT_SECONDS)
  
  timespan_span_all_variable = variables['timespan_span_all']
  
  def show_spinbox_frame():
    gui.enable_widget(spinbox_frame, enabled=not timespan_span_all_variable.get())
  
  show_spinbox_frame()
  
  timespan_span_all_checkbutton = ttk.Checkbutton(
    cell_frame,
    text='Span All',
    variable=timespan_span_all_variable,
    command=show_spinbox_frame
  )
  
  timespan_span_all_checkbutton.grid(row=0, column=1, sticky=tk.E, padx=gui.PADX_QW)
  return timespan_span_all_checkbutton


def make_background_noise_volume(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make scale frame horizontally resizable
  
  scale_frame = ttk.Frame(cell_frame)
  scale_frame.grid(row=0, column=0, sticky=tk.EW)
  gui.make_scale(scale_frame, variable=variables['background_noise_volume'])
  
  radiobuttons_frame = ttk.Frame(cell_frame)
  radiobuttons_frame.grid(row=0, column=1, sticky=tk.E, padx=gui.PADX_QW)
  
  radiobuttons = gui.make_widgets(
    radiobuttons_frame,
    ttk.Radiobutton,
    items=gui.text_widgets_items(('Log', 'Linear')),
    orient=tk.VERTICAL,
    cell=0,
    padding=gui.PADDING_Q
  )
  
  gui.link_radiobuttons(dict.fromkeys(radiobuttons),
    variables['background_noise_volume_loglinear'])
  
  return radiobuttons


def make_sort(frame, variables):
  frame.columnconfigure(0, weight=1) # make sort by frame horizontally resizable
  
  sort_by_frame = ttk.Frame(frame)
  sort_by_frame.grid(row=0, column=0, sticky=tk.EW)
  gui.make_combobox(sort_by_frame, name='Sort By', textvariable=variables['sort_by'],
    values=('Number of Sounds', 'File Name'), state=('readonly',))
  
  sort_reverse_checkbutton = None
  sort_reverse_variable = variables['sort_reverse']
  
  photo = gui.get_root_images()[gui.FSENC_PHOTO]
  up = photo[fsenc('up.gif')]
  down = photo[fsenc('down.gif')]
  
  def show_sort_reverse_checkbutton():
    sort_reverse_checkbutton['image'] = up if sort_reverse_variable.get() else down
  
  sort_reverse_checkbutton = ttk.Checkbutton(frame, width=1,
    variable=sort_reverse_variable, command=show_sort_reverse_checkbutton)
  
  sort_reverse_checkbutton.grid(row=0, column=1, sticky=tk.E, padx=gui.PADX_QW)
  show_sort_reverse_checkbutton()
  return sort_by_frame, sort_reverse_checkbutton


def make_items(frame, variables):
  frame.columnconfigure(0, weight=1) # make item delimiter frame horizontally resizable
  
  item_delimiter_frame = ttk.Frame(frame)
  item_delimiter_frame.grid(row=0, column=0, sticky=tk.EW)
  item_delimiter_variable = variables['item_delimiter']
  
  def invalid_item_delimiter(W, v):
    # item delimiter should be a space at minimum
    item_delimiter_variable.set(yamosse_output.DEFAULT_ITEM_DELIMITER)
    gui.after_invalidcommand_widget(item_delimiter_frame.nametowidget(W), v)
  
  item_delimiter_entry = gui.make_entry(
    item_delimiter_frame,
    name='Item Delimiter',
    textvariable=item_delimiter_variable,
    invalidcommand=(item_delimiter_frame.register(invalid_item_delimiter), '%W', '%v'),
    validatecommand=(item_delimiter_frame.register(lambda P: bool(P)), '%P'),
    validate='focusout'
  )[1]
  
  item_delimiter_entry.validate()
  
  indent_checkbutton = ttk.Checkbutton(frame,
    text='Indent', variable=variables['indent'])
  
  indent_checkbutton.grid(row=0, column=1, sticky=tk.E, padx=gui.PADX_QW)
  return item_delimiter_frame, indent_checkbutton


def make_spacer(frame):
  frame.rowconfigure(0, weight=1) # make label vertically centered
  
  ttk.Label(frame).grid()


def make_output_file_options(frame, variables):
  frame.columnconfigure(0, weight=1) # one column layout
  
  sort_frame = ttk.Frame(frame)
  sort_frame.grid(row=0, sticky=tk.EW)
  sort_by_frame, sort_reverse_checkbutton = make_sort(sort_frame, variables)
  
  items_frame = ttk.Frame(frame)
  items_frame.grid(row=1, sticky=tk.EW, pady=gui.PADY_QN)
  item_delimiter_frame, indent_checkbutton = make_items(items_frame, variables)
  
  output_options_checkbutton = ttk.Checkbutton(frame,
    text='Output Options', variable=variables['output_options'])
  
  output_options_checkbutton.grid(row=2, sticky=tk.W, pady=gui.PADY_QN)
  
  output_scores_checkbutton = ttk.Checkbutton(frame,
    text='Output Scores', variable=variables['output_scores'])
  
  # this is only sticky to W so Help only appears when mousing over the checkbutton itself
  output_scores_checkbutton.grid(row=3, sticky=tk.W, pady=gui.PADY_QN)
  
  frame_rows = frame.grid_size()[1]
  frame.rowconfigure(tuple(range(frame_rows)), weight=1,
    uniform='output_worker_options_row') # make the rows uniform
  
  return (
    sort_by_frame, sort_reverse_checkbutton,
    item_delimiter_frame, indent_checkbutton,
    output_options_checkbutton, output_scores_checkbutton
  )


def make_worker_options(frame, variables):
  frame.columnconfigure(0, weight=1) # one column layout
  
  memory_limit_frame = ttk.Frame(frame)
  memory_limit_frame.grid(row=0, sticky=tk.EW)
  gui.make_spinbox(memory_limit_frame, name='Memory Limit', textvariable=variables['memory_limit'],
    from_=1, to=64*1024, unit='MB')
  
  max_workers_frame = ttk.Frame(frame)
  max_workers_frame.grid(row=1, sticky=tk.EW, pady=gui.PADY_QN)
  gui.make_spinbox(max_workers_frame, name='Max Workers', textvariable=variables['max_workers'],
    from_=1, to=512)
  
  high_priority_checkbutton = ttk.Checkbutton(frame,
    text='High Priority', variable=variables['high_priority'])
  
  high_priority_checkbutton.grid(row=2, sticky=tk.W, pady=gui.PADY_QN)
  
  spacer_frame = ttk.Frame(frame)
  spacer_frame.grid(row=3, pady=gui.PADY_QN)
  make_spacer(spacer_frame)
  
  frame_rows = frame.grid_size()[1]
  frame.rowconfigure(tuple(range(frame_rows)), weight=1,
    uniform='output_worker_options_row') # make the rows uniform
  
  return memory_limit_frame, max_workers_frame, high_priority_checkbutton


def _link_tips(text, tips):
  stack = []
  
  def show(e, tip=''):
    text['state'] = tk.NORMAL
    
    try:
      if tip:
        widget = e.widget
        
        # it is possible to recieve more than one Enter event before Leave event
        # (on comboboxes)
        # so we must check if this is the same widget as the one on top of the stack
        if stack and widget is stack[-1]:
          return
        
        text.delete('1.0', tk.END)
        text.insert(tk.END, tip)
        text.edit_separator()
        
        stack.append(widget)
      elif stack:
        stack.pop()
        
        # revert tip when moving from a child widget to its parent frame
        text.edit_undo()
        text.edit_separator()
    finally:
      text['state'] = tk.DISABLED
  
  for widget, tip in tips.items():
    widget.bind('<Enter>', lambda e, tip=tip: show(e, tip), add=True)
    widget.bind('<Leave>', show, add=True)


def make_advanced(frame, variables, weights_filetypes, tfhub_enabled):
  frame.rowconfigure(3, weight=1) # make tips frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=0, sticky=tk.NSEW)
  
  row_frame.columnconfigure((0, 1), weight=1, uniform='advanced_column') # make the columns uniform
  
  timespan_labelframe = ttk.Labelframe(row_frame, text='Timespan',
    padding=gui.PADDING_HNSEW)
  
  timespan_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui.PADX_HE)
  timespan_span_all_checkbutton = make_timespan(timespan_labelframe, variables)
  
  background_noise_volume_labelframe = ttk.Labelframe(row_frame, text='Background Noise Volume',
    padding=gui.PADDING_HNSEW)
  
  background_noise_volume_labelframe.grid(row=0, column=1, sticky=tk.NSEW, padx=gui.PADX_HW)
  background_noise_volume_radiobuttons = make_background_noise_volume(
    background_noise_volume_labelframe, variables)
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_QN)
  
  row_frame.columnconfigure((0, 1), weight=1, uniform='advanced_column') # make the columns uniform
  
  output_file_options_labelframe = ttk.Labelframe(row_frame, text='Output File Options',
    padding=gui.PADDING_HNSEW)
  
  output_file_options_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui.PADX_HE)
  output_file_options_widgets = make_output_file_options(output_file_options_labelframe, variables)
  
  worker_options_labelframe = ttk.Labelframe(row_frame, text='Worker Options',
    padding=gui.PADDING_HNSEW)
  
  worker_options_labelframe.grid(row=0, column=1, sticky=tk.NSEW, padx=gui.PADX_HW)
  worker_options_widgets = make_worker_options(worker_options_labelframe, variables)
  
  weights_labelframe = ttk.Labelframe(frame, text='Weights', padding=gui.PADDING_HNSEW)
  weights_labelframe.grid(row=2, sticky=tk.NSEW, pady=gui.PADY_QN)
  gui.make_filedialog(weights_labelframe, textvariable=variables['weights'],
    parent=frame.winfo_toplevel(), filetypes=weights_filetypes)
  
  if tfhub_enabled: gui.enable_widget(weights_labelframe, enabled=False)
  
  tips_labelframe = ttk.Labelframe(frame, text='Tips', padding=gui.PADDING_HNSEW)
  tips_labelframe.grid(row=3, sticky=tk.NSEW, pady=gui.PADY_QN)
  tips_text = gui.make_text(tips_labelframe,
    takefocus=False, undo=True, autoseparators=False, yscroll=False)[1][0]
  
  gui.prevent_default_widget(tips_text) # no selection when double clicking
  gui.enable_widget(tips_text, enabled=False)
  
  _link_tips(tips_text, {
    weights_labelframe: TIP_WEIGHTS,
    
    timespan_labelframe: TIP_TIMESPAN,
    timespan_span_all_checkbutton: TIP_TIMESPAN_SPAN_ALL,
    
    background_noise_volume_labelframe: TIP_BACKGROUND_NOISE_VOLUME,
    background_noise_volume_radiobuttons[0]: TIP_BACKGROUND_NOISE_VOLUME_LOG,
    background_noise_volume_radiobuttons[1]: TIP_BACKGROUND_NOISE_VOLUME_LINEAR,
    
    output_file_options_widgets[0]: TIP_OUTPUT_FILE_OPTIONS_SORT_BY,
    output_file_options_widgets[1]: TIP_OUTPUT_FILE_OPTIONS_SORT_REVERSE,
    output_file_options_widgets[2]: TIP_OUTPUT_FILE_OPTIONS_ITEM_DELIMITER,
    output_file_options_widgets[3]: TIP_OUTPUT_FILE_OPTIONS_INDENT,
    output_file_options_widgets[4]: TIP_OUTPUT_FILE_OPTIONS_OUTPUT_OPTIONS,
    output_file_options_widgets[5]: TIP_OUTPUT_FILE_OPTIONS_OUTPUT_SCORE,
    
    worker_options_widgets[0]: TIP_WORKER_OPTIONS_MEMORY_LIMIT,
    worker_options_widgets[1]: TIP_WORKER_OPTIONS_MAX_WORKERS,
    worker_options_widgets[2]: TIP_WORKER_OPTIONS_HIGH_PRIORITY
  })


def make_options(notebook, variables,
  input_filetypes, class_names, weights_filetypes, tfhub_enabled,
  import_preset, export_preset):
  notebook['style'] = 'Raised.TNotebook'
  
  general_frame = ttk.Frame(notebook, padding=gui.PADDING_NSEW,
    style='Raised.TNotebook > .TFrame')
  
  make_general(general_frame, variables, input_filetypes, class_names,
    import_preset, export_preset)
  
  advanced_frame = ttk.Frame(notebook, padding=gui.PADDING_NSEW,
    style='Raised.TNotebook > .TFrame')
  
  make_advanced(advanced_frame, variables, weights_filetypes, tfhub_enabled)
  
  notebook.add(general_frame, text='General', underline=0, sticky=tk.NSEW)
  notebook.add(advanced_frame, text='Advanced', underline=0, sticky=tk.NSEW)
  notebook.enable_traversal()


def make_footer(frame, yamscan, restore_defaults):
  frame.columnconfigure(1, weight=1)
  
  def open_online_help():
    webbrowser.open(URL_ONLINE_HELP)
  
  open_online_help_button = ttk.Button(frame, text='Open Online Help',
    image=gui.get_root_images()[gui.FSENC_PHOTO][fsenc('help symbol.gif')], compound=tk.LEFT,
    command=open_online_help)
  
  open_online_help_button.grid(row=0, column=0, sticky=tk.W)
  open_online_help_button.winfo_toplevel().bind('<F1>', lambda e: open_online_help())
  
  yamscan_button = ttk.Button(frame, text='YAMScan!', underline=0,
    command=yamscan)
  
  yamscan_button.grid(row=0, column=2, sticky=tk.E)
  
  restore_defaults_button = ttk.Button(frame, text='Restore Defaults', underline=0,
    command=restore_defaults)
  
  restore_defaults_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  
  for button in (yamscan_button, restore_defaults_button):
    gui.enable_traversal_button(button)


def make_yamosse(frame, title, options_variables,
  input_filetypes, class_names, weights_filetypes, tfhub_enabled,
  import_preset, export_preset, yamscan, restore_defaults):
  window = frame.master
  gui.customize_window(window, title, resizable=RESIZABLE, size=SIZE,
    iconphotos=gui.get_root_images()[gui.FSENC_PHOTO][fsenc('emoji_u1f3a4')].values())
  
  frame.rowconfigure(1, weight=1) # make options frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  header_frame = ttk.Frame(frame)
  header_frame.grid(row=0, sticky=tk.EW)
  make_header(header_frame, title)
  
  options_notebook = ttk.Notebook(frame)
  options_notebook.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_N)
  make_options(options_notebook, options_variables,
    input_filetypes, class_names, weights_filetypes, tfhub_enabled,
    import_preset, export_preset)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=2, sticky=tk.EW, pady=gui.PADY_N)
  make_footer(footer_frame, yamscan, restore_defaults)