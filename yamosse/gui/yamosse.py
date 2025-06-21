import tkinter as tk
from tkinter import ttk
import webbrowser

from . import gui as gui
from . import std as gui_std

MINSIZE_ROW_LABELS = 21
MINSIZE_ROW_RADIOBUTTONS = MINSIZE_ROW_LABELS

MESSAGE_INPUT_NONE = 'You must select an input folder or files first.'

MESSAGE_WEIGHTS_NONE = ''.join(('You have not specified the weights file. Would you like to ',
  'download the standard YAMNet weights now from Google Cloud Storage? If you click No, the ',
  'YAMScan will be cancelled.'))

MESSAGE_IMPORT_PRESET_VERSION = 'The imported preset is not compatible with this YAMosse version.'
MESSAGE_IMPORT_PRESET_INVALID = 'The imported preset is invalid.'

ASK_RESTORE_DEFAULTS_MESSAGE = 'Are you sure you want to restore the defaults?'

WEIGHTS_TIP = ''.join(('The YAMNet Weights file. This option will be disabled if you are using ',
  'the Tensorflow Hub release of YAMNet.'))

COMBINE_TIP = ''.join(('If a sound is less than this length in seconds, it will be combined into ',
  'one timestamp. Otherwise, the beginning and ending timestamp will be output with a dash ',
  'inbetween. To always combine timestamps, set this to zero.'))

COMBINE_ALL_TIP = ''.join(('If checked, timestamps are not used. Instead, one prediction is made ',
  'for the entire sound file.'))

BACKGROUND_NOISE_VOLUME_TIP = ''.join(('The volume below which all sounds are ignored. Setting ',
  'this to at least 1% will make scans significantly faster during silent parts of the sound ',
  'file. Set this to 0% to scan everything.'))

BACKGROUND_NOISE_VOLUME_LOG_TIP = ''.join(('Logarithmic volume scale (with a 60 dB range.) This ',
  'is the volume scale you should use in most cases.'))

BACKGROUND_NOISE_VOLUME_LINEAR_TIP = 'Linear volume scale.'

OUTPUT_OPTIONS_SORT_BY_TIP = ''.join(('Whether to sort results by the number of sounds ',
  'identified, or alphabetically by file name.'))

OUTPUT_OPTIONS_ITEM_DELIMITER_TIP = ''.join(('Seperator inbetween each timestamp or class. ',
  'Escape characters are supported.'))

OUTPUT_OPTIONS_OUTPUT_OPTIONS_TIP = 'Output the options that were used for the YAMScan.'

OUTPUT_OPTIONS_OUTPUT_CONFIDENCE_SCORE_TIP = ''.join(('Output the confidence score percentage ',
  'along with each timestamp, so you can see how certain the model is that it identified a sound ',
  'at that timestamp.'))

WORKER_OPTIONS_MEMORY_LIMIT_TIP = ''.join(('The per-worker Tensorflow logical device memory ',
  'limit, in megabytes.'))

WORKER_OPTIONS_MAX_WORKERS_TIP = ''.join(('Increasing the max number of workers may make scans ',
  'faster, unless it is set too high - then you might run out of memory (workers cost memory, ',
  'though adjusting the memory limit will make them cost less.)'))

WORKER_OPTIONS_HIGH_PRIORITY_TIP = ''.join(('Mark YAMosse as High Priority to make scans faster, ',
  'at the expense of other programs running slower.'))

HELP_URL = 'https://github.com/tomysshadow/YAMosse/blob/main/README.md'


def make_header(frame, title):
  ttk.Label(frame, text=title, style='Title.TLabel').grid()


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
  gui_std.make_scale(scale_frame, variables['confidence_score'])
  
  radiobuttons_frame = ttk.Frame(cell_frame)
  radiobuttons_frame.grid(row=0, column=1, sticky=tk.E, padx=gui_std.PADX_QW)
  radiobuttons = gui_std.make_widgets(radiobuttons_frame, ttk.Radiobutton,
    ('Min', 'Max'), orient=tk.VERTICAL, cell=0, padding=gui_std.PADDING_Q)
  
  gui_std.link_radiobuttons(zip(radiobuttons, (None,) * len(radiobuttons)),
    variables['confidence_score_minmax'])


def make_top_ranked(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make spinbox frame horizontally resizable
  
  spinbox_frame = ttk.Frame(cell_frame)
  spinbox_frame.grid(row=0, sticky=tk.EW)
  gui_std.make_spinbox(spinbox_frame, variables['top_ranked'],
    from_=1, unit=gui_std.UNIT_CLASSES)
  
  ttk.Checkbutton(cell_frame,
    variable=variables['top_ranked_output_timestamps'], text='Output Timestamps').grid(
    row=1, sticky=tk.W, pady=gui_std.PADY_QN)


def make_identification_options(frame, variables):
  frame.rowconfigure(0, minsize=MINSIZE_ROW_RADIOBUTTONS) # make radiobuttons minimum size
  
  frame.columnconfigure((0, 1), weight=1,
    uniform='identification_options_column') # make the columns uniform
  
  confidence_score_frame = ttk.Frame(frame)
  confidence_score_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=gui_std.PADX_HE)
  make_confidence_score(confidence_score_frame, variables)
  
  top_ranked_frame = ttk.Frame(frame)
  top_ranked_frame.grid(row=1, column=1, sticky=tk.NSEW, padx=gui_std.PADX_HW)
  make_top_ranked(top_ranked_frame, variables)
  
  radiobuttons = gui_std.make_widgets(frame, ttk.Radiobutton,
    ('Confidence Score', 'Top Ranked'), sticky=tk.EW, cell=0)
  
  gui_std.link_radiobuttons(zip(radiobuttons, (confidence_score_frame, top_ranked_frame)),
    variables['identification'])
  
  # fix tab order
  confidence_score_frame.lift()
  top_ranked_frame.lift()


def make_presets(frame, import_, export):
  frame.rowconfigure((0, 1), weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  import_button, export_button = gui_std.make_widgets(
    frame, ttk.Button, ('Import...', 'Export...'),
    orient=tk.VERTICAL, padding=gui_std.PADDING_Q)
  
  import_button['command'] = import_
  export_button['command'] = export


def make_general(frame, variables, input_filetypes, class_names, import_preset, export_preset):
  frame.rowconfigure(1, weight=1) # make classes frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  input_labelframe = ttk.Labelframe(frame, text='Input',
    padding=gui_std.PADDING_HNSEW)
  
  input_labelframe.grid(row=0, sticky=tk.NSEW)
  
  input_filedialog_buttons_frame = gui_std.make_filedialog(
    input_labelframe,
    variables['input_'],
    asks=('directory', 'openfilenames'),
    parent=frame.winfo_toplevel(),
    filetypes=input_filetypes
  )[2][0]
  
  input_recursive_checkbutton = ttk.Checkbutton(input_filedialog_buttons_frame,
    text='Recursive', variable=variables['input_recursive'])
  
  input_recursive_checkbutton.grid(row=0, column=gui_std.BUTTONS_COLUMN_LEFT)
  input_recursive_checkbutton.lower() # fix tab order
  
  classes_labelframe = ttk.Labelframe(frame, text='Classes',
    padding=gui_std.PADDING_HNSEW)
  
  classes_labelframe.grid(row=1, sticky=tk.NSEW, pady=gui_std.PADY_QN)
  classes_listbox_buttons_frame = gui_std.make_listbox(classes_labelframe, class_names,
    selectmode=tk.MULTIPLE)[2][0]
  
  # TODO command
  classes_calibrate_button = ttk.Button(classes_listbox_buttons_frame, text='Calibrate...')
  classes_calibrate_button.grid(row=0, column=gui_std.BUTTONS_COLUMN_LEFT)
  classes_calibrate_button.lower() # fix tab order
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=2, sticky=tk.NSEW, pady=gui_std.PADY_QN)
  
  row_frame.columnconfigure(0, weight=1) # make identification options frame horizontally resizable
  
  identification_options_labelframe = ttk.Labelframe(row_frame, text='Identification Options',
    padding=gui_std.PADDING_HNSEW)
  
  identification_options_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui_std.PADX_HE)
  make_identification_options(identification_options_labelframe, variables)
  
  presets_labelframe = ttk.Labelframe(row_frame, text='Presets',
    padding=gui_std.PADDING_HNSEW)
  
  presets_labelframe.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E), padx=gui_std.PADX_HW)
  make_presets(presets_labelframe, import_preset, export_preset)


def make_combine(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make spinbox frame horizontally resizable
  
  spinbox_frame = ttk.Frame(cell_frame)
  spinbox_frame.grid(row=0, column=0, sticky=tk.EW)
  gui_std.make_spinbox(spinbox_frame, variables['combine'],
    from_=0, to=60, unit=gui_std.UNIT_SECONDS)
  
  combine_all_checkbutton = ttk.Checkbutton(
    cell_frame,
    variable=variables['combine_all'],
    text='All',
    command=lambda: gui_std.enable_widget(spinbox_frame,
      enabled=not variables['combine_all'].get())
  )
  
  combine_all_checkbutton.grid(row=0, column=1, sticky=tk.E, padx=gui_std.PADX_QW)
  return combine_all_checkbutton


def make_background_noise_volume(frame, variables):
  frame.rowconfigure(0, weight=1) # make cell frame vertically centered
  frame.columnconfigure(0, weight=1) # make cell frame horizontally resizable
  
  cell_frame = ttk.Frame(frame)
  cell_frame.grid(sticky=tk.EW)
  
  cell_frame.columnconfigure(0, weight=1) # make scale frame horizontally resizable
  
  scale_frame = ttk.Frame(cell_frame)
  scale_frame.grid(row=0, column=0, sticky=tk.EW)
  gui_std.make_scale(scale_frame, variables['background_noise_volume'])
  
  radiobuttons_frame = ttk.Frame(cell_frame)
  radiobuttons_frame.grid(row=0, column=1, sticky=tk.E, padx=gui_std.PADX_QW)
  radiobuttons = gui_std.make_widgets(radiobuttons_frame, ttk.Radiobutton,
    ('Log', 'Linear'), orient=tk.VERTICAL, cell=0, padding=gui_std.PADDING_Q)
  
  gui_std.link_radiobuttons(zip(radiobuttons, (None,) * len(radiobuttons)),
    variables['background_noise_volume_loglinear'])
  
  return radiobuttons


def make_spacer(frame):
  frame.rowconfigure(0, weight=1) # make label vertically centered
  
  ttk.Label(frame).grid()


def make_output_options(frame, variables):
  frame.columnconfigure(0, weight=1) # one column layout
  
  sort_by_frame = ttk.Frame(frame)
  sort_by_frame.grid(row=0, sticky=tk.EW)
  gui_std.make_combobox(sort_by_frame, variables['sort_by'], name='Sort By',
    values=('Number of Sounds', 'File Name'), state=('readonly',))
  
  item_delimiter_frame = ttk.Frame(frame)
  item_delimiter_frame.grid(row=1, sticky=tk.EW, pady=gui_std.PADY_QN)
  item_delimiter_variable = variables['item_delimiter']
  item_delimiter_entry = gui_std.make_entry(
    item_delimiter_frame, item_delimiter_variable, name='Item Delimiter')[1]
  
  # item delimiter should be a space at minimum
  def focus_out_item_delimiter(e=None):
    if not item_delimiter_variable.get(): item_delimiter_variable.set(' ')
  
  item_delimiter_entry.bind('<FocusOut>', focus_out_item_delimiter)
  focus_out_item_delimiter()
  
  output_options_checkbutton = ttk.Checkbutton(frame,
    variable=variables['output_options'], text='Output Options')
  
  output_options_checkbutton.grid(row=2, sticky=tk.W, pady=gui_std.PADY_QN)
  
  output_confidence_scores_checkbutton = ttk.Checkbutton(frame,
    variable=variables['output_confidence_scores'], text='Output Confidence Scores')
  
  # this is only sticky to W so Help only appears when mousing over the checkbutton itself
  output_confidence_scores_checkbutton.grid(row=3, sticky=tk.W, pady=gui_std.PADY_QN)
  
  frame_rows = frame.grid_size()[1]
  frame.rowconfigure(tuple(range(frame_rows)), weight=1,
    uniform='output_worker_options_row') # make the rows uniform
  
  return (sort_by_frame, item_delimiter_frame, output_options_checkbutton,
    output_confidence_scores_checkbutton)


def make_worker_options(frame, variables):
  frame.columnconfigure(0, weight=1) # one column layout
  
  memory_limit_frame = ttk.Frame(frame)
  memory_limit_frame.grid(row=0, sticky=tk.EW)
  gui_std.make_spinbox(memory_limit_frame, variables['memory_limit'], name='Memory Limit',
    from_=1, to=4096, unit='MB')
  
  max_workers_frame = ttk.Frame(frame)
  max_workers_frame.grid(row=1, sticky=tk.EW, pady=gui_std.PADY_QN)
  gui_std.make_spinbox(max_workers_frame, variables['max_workers'], name='Max Workers',
    from_=1, to=512)
  
  high_priority_checkbutton = ttk.Checkbutton(frame,
    variable=variables['high_priority'], text='High Priority')
  
  high_priority_checkbutton.grid(row=2, sticky=tk.W, pady=gui_std.PADY_QN)
  
  spacer_frame = ttk.Frame(frame)
  spacer_frame.grid(row=3, pady=gui_std.PADY_QN)
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
        if stack and widget == stack[-1]:
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
    widget.bind('<Enter>', lambda e, tip=tip: show(e, tip))
    widget.bind('<Leave>', show)


def make_advanced(frame, variables, weights_filetypes, tfhub_enabled):
  frame.rowconfigure(3, weight=1) # make tips frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=0, sticky=tk.NSEW)
  
  row_frame.columnconfigure((0, 1), weight=1,
    uniform='advanced_column') # make the columns uniform
  
  combine_labelframe = ttk.Labelframe(row_frame, text='Combine',
    padding=gui_std.PADDING_HNSEW)
  
  combine_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui_std.PADX_HE)
  combine_all_checkbutton = make_combine(combine_labelframe, variables)
  
  background_noise_volume_labelframe = ttk.Labelframe(row_frame, text='Background Noise Volume',
    padding=gui_std.PADDING_HNSEW)
  
  background_noise_volume_labelframe.grid(row=0, column=1, sticky=tk.NSEW, padx=gui_std.PADX_HW)
  background_noise_volume_radiobuttons = make_background_noise_volume(
    background_noise_volume_labelframe, variables)
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui_std.PADY_QN)
  
  row_frame.columnconfigure((0, 1), weight=1,
    uniform='advanced_column') # make the columns uniform
  
  output_options_labelframe = ttk.Labelframe(row_frame, text='Output Options',
    padding=gui_std.PADDING_HNSEW)
  
  output_options_labelframe.grid(row=0, column=0, sticky=tk.NSEW, padx=gui_std.PADX_HE)
  output_options_widgets = make_output_options(output_options_labelframe, variables)
  
  worker_options_labelframe = ttk.Labelframe(row_frame, text='Worker Options',
    padding=gui_std.PADDING_HNSEW)
  
  worker_options_labelframe.grid(row=0, column=1, sticky=tk.NSEW, padx=gui_std.PADX_HW)
  worker_options_widgets = make_worker_options(worker_options_labelframe, variables)
  
  weights_labelframe = ttk.Labelframe(frame, text='Weights', padding=gui_std.PADDING_HNSEW)
  weights_labelframe.grid(row=2, sticky=tk.NSEW, pady=gui_std.PADY_QN)
  gui_std.make_filedialog(weights_labelframe, variables['weights'],
    parent=frame.winfo_toplevel(), filetypes=weights_filetypes)
  
  if tfhub_enabled: gui_std.enable_widget(weights_labelframe, enabled=False)
  
  tips_labelframe = ttk.Labelframe(frame, text='Tips', padding=gui_std.PADDING_HNSEW)
  tips_labelframe.grid(row=3, sticky=tk.NSEW, pady=gui_std.PADY_QN)
  tips_text = gui_std.make_text(tips_labelframe,
    takefocus=False, undo=True, yscroll=False)[1][0]
  
  gui_std.prevent_default_widget(tips_text) # no selection when double clicking
  gui_std.enable_widget(tips_text, enabled=False)
  
  _link_tips(tips_text, {
    weights_labelframe: WEIGHTS_TIP,
    
    combine_labelframe: COMBINE_TIP,
    combine_all_checkbutton: COMBINE_ALL_TIP,
    
    background_noise_volume_labelframe: BACKGROUND_NOISE_VOLUME_TIP,
    background_noise_volume_radiobuttons[0]: BACKGROUND_NOISE_VOLUME_LOG_TIP,
    background_noise_volume_radiobuttons[1]: BACKGROUND_NOISE_VOLUME_LINEAR_TIP,
    
    output_options_widgets[0]: OUTPUT_OPTIONS_SORT_BY_TIP,
    output_options_widgets[1]: OUTPUT_OPTIONS_ITEM_DELIMITER_TIP,
    output_options_widgets[2]: OUTPUT_OPTIONS_OUTPUT_OPTIONS_TIP,
    output_options_widgets[3]: OUTPUT_OPTIONS_OUTPUT_CONFIDENCE_SCORE_TIP,
    
    worker_options_widgets[0]: WORKER_OPTIONS_MEMORY_LIMIT_TIP,
    worker_options_widgets[1]: WORKER_OPTIONS_MAX_WORKERS_TIP,
    worker_options_widgets[2]: WORKER_OPTIONS_HIGH_PRIORITY_TIP
  })


def make_options(frame, variables,
  input_filetypes, weights_filetypes, class_names, tfhub_enabled,
  import_preset, export_preset):
  frame.rowconfigure(0, weight=1) # make notebook vertically resizable
  frame.columnconfigure(0, weight=1) # make notebook horizontally resizable
  
  notebook = ttk.Notebook(frame, style='Borderless.TNotebook')
  notebook.grid(sticky=tk.NSEW)
  
  general_frame = ttk.Frame(notebook, padding=gui_std.PADDING_NSEW, relief=tk.RAISED)
  make_general(general_frame, variables, input_filetypes, class_names,
    import_preset, export_preset)
  
  advanced_frame = ttk.Frame(notebook, padding=gui_std.PADDING_NSEW, relief=tk.RAISED)
  make_advanced(advanced_frame, variables, weights_filetypes, tfhub_enabled)
  
  notebook.add(general_frame, text='General', underline=0, sticky=tk.NSEW)
  notebook.add(advanced_frame, text='Advanced', underline=0, sticky=tk.NSEW)
  notebook.enable_traversal()


def make_footer(frame, yamscan, restore_defaults):
  frame.columnconfigure(1, weight=1)
  
  def help_():
    webbrowser.open(HELP_URL)
  
  help_button = ttk.Button(frame, text='Help', width=6,
    image=gui.get_root_images()['Photo']['help.gif'], compound=tk.LEFT,
    command=help_)
  
  help_button.grid(row=0, column=0, sticky=tk.W)
  help_button.winfo_toplevel().bind('<F1>', lambda e: help_())
  
  yamscan_button = ttk.Button(frame, text='YAMScan!', underline=0,
    command=yamscan)
  
  yamscan_button.grid(row=0, column=2, sticky=tk.E)
  
  restore_defaults_button = ttk.Button(frame, text='Restore Defaults', underline=0,
    command=restore_defaults)
  
  restore_defaults_button.grid(row=0, column=3, sticky=tk.E, padx=gui_std.PADX_QW)
  
  for button in (
    yamscan_button, restore_defaults_button):
    gui_std.enable_traversal_button(button)


def make_yamosse(frame, title, options_variables,
  input_filetypes, weights_filetypes, class_names, tfhub_enabled,
  yamscan, import_preset, export_preset, restore_defaults):
  # resizing technically works but looks kind of jank, so just disable for now
  RESIZABLE = False
  SIZE = (600, 560)
  
  window = frame.master
  gui.customize_window(window, title, resizable=RESIZABLE, size=SIZE,
    iconphotos=gui.get_root_images()['Photo']['emoji_u1f3a4'].values())
  
  frame.rowconfigure(1, weight=1) # make options frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  header_frame = ttk.Frame(frame)
  header_frame.grid(row=0, sticky=tk.EW)
  make_header(header_frame, title)
  
  options_frame = ttk.Frame(frame)
  options_frame.grid(row=1, sticky=tk.NSEW, pady=gui_std.PADY_N)
  make_options(options_frame, options_variables,
    input_filetypes, weights_filetypes, class_names, tfhub_enabled,
    import_preset, export_preset)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=2, sticky=tk.EW, pady=gui_std.PADY_N)
  make_footer(footer_frame, yamscan, restore_defaults)