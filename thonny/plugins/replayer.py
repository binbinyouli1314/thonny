import tkinter as tk
import tkinter.ttk as ttk
from datetime import datetime
from thonny import ui_utils
from thonny.globals import get_workbench
import json
from thonny.base_file_browser import BaseFileBrowser
import ast


class ReplayWindow(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self, get_workbench())
        ui_utils.set_zoomed(self, True)
        
        self.main_pw   = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.center_pw  = ttk.PanedWindow(self.main_pw, orient=tk.VERTICAL)
        self.right_frame = ttk.Frame(self.main_pw)
        self.editor_notebook = ReplayerEditorNotebook(self.center_pw)
        shell_book = ttk.Notebook(self.main_pw)
        self.shell = ShellFrame(shell_book)
        self.log_frame = LogFrame(self.right_frame, self.editor_notebook, self.shell)
        self.browser = ReplayerFileBrowser(self.main_pw, self.log_frame)
        self.control_frame = ControlFrame(self.right_frame)
        
        self.main_pw.grid(padx=10, pady=10, sticky=tk.NSEW)
        self.main_pw.add(self.browser, weight=1)
        self.main_pw.add(self.center_pw, weight=3)
        self.main_pw.add(self.right_frame, weight=1)
        self.center_pw.add(self.editor_notebook, weight=3)
        self.center_pw.add(shell_book, weight=1)
        shell_book.add(self.shell, text="Shell")
        self.log_frame.grid(sticky=tk.NSEW)
        self.control_frame.grid(sticky=tk.NSEW)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
            

class ReplayerFileBrowser(BaseFileBrowser):
    
    def __init__(self, master, log_frame):
        BaseFileBrowser.__init__(self, master, True, "tools.replayer_last_browser_folder")
        self.log_frame = log_frame
        self.configure(border=1, relief=tk.GROOVE)

    def on_double_click(self, event):
        self.save_current_folder()
        path = self.get_selected_path()
        if path:
            self.log_frame.load_log(path)
            
class ControlFrame(ttk.Frame):
    def __init__(self, master, **kw):
        ttk.Frame.__init__(self, master=master, **kw)
        
        self.toggle_button = ttk.Button(self, text="Play")
        self.speed_scale = ttk.Scale(self, from_=1, to=100, orient=tk.HORIZONTAL)
        
        self.toggle_button.grid(row=0, column=0, sticky=tk.NSEW, pady=(10,0), padx=(0,5))
        self.speed_scale.grid(row=0, column=1, sticky=tk.NSEW, pady=(10,0), padx=(5,0))
        
        self.columnconfigure(1, weight=1)
        
        

class LogFrame(ui_utils.TreeFrame):
    def __init__(self, master, editor_book, shell):
        ui_utils.TreeFrame.__init__(self, master, ("desc", "pause", "time"))
        self.configure(border=1, relief=tk.GROOVE)
        
        self.editor_notebook = editor_book
        self.shell = shell
        self.all_events = []
        self.last_event_index = -1
        self.loading = False 

    def load_log(self, filename):
        self._clear_tree()
        self.all_events = []
        self.last_event_index = -1
        self.loading = True
        self.editor_notebook.clear()
        self.shell.clear()
        
        with open(filename, encoding="UTF-8") as f:
            events = json.load(f)
            last_event_time = None
            for event in events:
                node_id = self.tree.insert("", "end")
                self.tree.set(node_id, "desc", repr(event))
                event_time = datetime.strptime(event["time"], "%Y-%m-%dT%H:%M:%S.%f")
                if last_event_time:
                    delta = event_time - last_event_time
                    pause = delta.seconds
                else:
                    pause = 0   
                self.tree.set(node_id, "pause", str(pause if pause else ""))
                self.tree.set(node_id, "time", str(event["time"]))
                self.all_events.append(event)

                last_event_time = event_time
                
        self.loading = False
        
    def replay_event(self, event):
        "this should be called with events in correct order"
        #print("log replay", event)
        
        if "text_widget_id" in event:
            if event.get("text_widget_context", None) == "shell":
                self.shell.replay_event(event)
            else:
                self.editor_notebook.replay_event(event)
    
    def undo_event(self, event):
        "this should be called with events in correct order"
        #print("log undo", event)
        if "text_widget_id" in event:
            if event.get("text_widget_context", None) == "shell":
                self.shell.undo_event(event)
            else:
                self.editor_notebook.undo_event(event)
    
    def on_select(self, event):
        # parameter "event" is here tkinter event
        if self.loading:
            return 
        iid = self.tree.focus()
        if iid != '':
            self.select_event(self.tree.index(iid))
        
    def select_event(self, event_index):
        # here event means logged event
        if event_index > self.last_event_index:
            # replay all events between last replayed event up to and including this event
            while self.last_event_index < event_index:
                self.replay_event(self.all_events[self.last_event_index+1])
                self.last_event_index += 1
                
        elif event_index < self.last_event_index:
            # undo all events up to and excluding this event
            while self.last_event_index > event_index:
                self.undo_event(self.all_events[self.last_event_index])
                self.last_event_index -= 1


class ReplayerCodeView(ttk.Frame):
    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        
        self.vbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.vbar.grid(row=0, column=2, sticky=tk.NSEW)
        self.hbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.hbar.grid(row=1, column=0, sticky=tk.NSEW, columnspan=2)
        self.text = tk.Text(self,
                yscrollcommand=self.vbar.set,
                xscrollcommand=self.hbar.set,
                borderwidth=0,
                font=get_workbench().get_font("EditorFont"),
                wrap=tk.NONE,
                insertwidth=2,
                #selectborderwidth=2,
                inactiveselectbackground='gray',
                #highlightthickness=0, # TODO: try different in Mac and Linux
                #highlightcolor="gray",
                padx=5,
                pady=5,
                undo=True,
                autoseparators=False)
        
        self.text.grid(row=0, column=1, sticky=tk.NSEW)
        self.hbar['command'] = self.text.xview
        self.vbar['command'] = self.text.yview
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        

class ReplayerEditor(ttk.Frame):
    def __init__(self, master):
        ttk.Frame.__init__(self, master)
        self.code_view = ReplayerCodeView(self)
        self.code_view.grid(sticky=tk.NSEW)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text_states_before = {} # self.text_states[event_id] contains editor content before event with id event_id
    
    def replay_event(self, event):
        if event["sequence"] in ["TextInsert", "TextDelete"]:
            self.text_states_before[id(event)] = self.code_view.text.get("1.0", "end")
            self.see_event(event)
            
            if event["sequence"] == "TextInsert":
                self.code_view.text.insert(event["index"], event["text"],
                                           ast.literal_eval(event["tags"]))
                
            elif event["sequence"] == "TextDelete":
                if event["index2"]:
                    self.code_view.text.delete(event["index1"], event["index2"])
                else:
                    self.code_view.text.delete(event["index1"])
        
    
    def undo_event(self, event):
        if id(event) in self.text_states_before:
            self.code_view.text.delete("1.0", "end")
            self.code_view.text.insert("1.0", self.text_states_before[id(event)])
            self.see_event(event)
    
    def see_event(self, event):
        if hasattr(event, "to_position") and event.to_position:
            self.code_view.text.see(event.to_position)
            
        if hasattr(event, "from_position") and event.from_position:
            self.code_view.text.see(event.from_position)
            
        if hasattr(event, "position") and event.position:
            self.code_view.text.see(event.position)

class ReplayerEditorNotebook(ttk.Notebook):
    def __init__(self, master):
        ttk.Notebook.__init__(self, master, padding=0)
        self._editors_by_text_widget_id = {}
    
    def clear(self):
        
        for child in self.winfo_children():
            child.destroy()
        
        self._editors_by_text_widget_id = {}
    
    def get_editor_by_text_widget_id(self, text_widget_id):
        if text_widget_id not in self._editors_by_text_widget_id:
            editor = ReplayerEditor(self)
            self.add(editor, text="<untitled>")
            self._editors_by_text_widget_id[text_widget_id] = editor
            
        return self._editors_by_text_widget_id[text_widget_id]
    
    def replay_event(self, event):
        if "text_widget_id" in event:
            editor = self.get_editor_by_text_widget_id(event["text_widget_id"])
            #print(event.editor_id, id(editor), event)
            self.select(editor)
            editor.replay_event(event)
    
    def undo_event(self, event):
        if "text_widget_id" in event:
            editor = self.get_editor_by_text_widget_id(event["text_widget_id"])
            editor.undo_event(event)

class ShellFrame(ReplayerEditor):
    def clear(self):
        self.code_view.text.delete("1.0", "end")


def load_plugin():
    def open_replayer():
        win = ReplayWindow()
        win.focus_set()
        win.grab_set()
        get_workbench().wait_window(win)
    
    get_workbench().add_option("tools.replayer_last_browser_folder", None)
    if (get_workbench().get_option("debug_mode")
        or get_workbench().get_option("expert_mode")):
        get_workbench().add_command("open_replayer", "tools", "Open replayer", 
                                open_replayer)