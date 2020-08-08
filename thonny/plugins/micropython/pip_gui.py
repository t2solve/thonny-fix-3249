import os
import shutil
import subprocess
import tempfile
import tkinter as tk
from tkinter.messagebox import showerror
from tkinter import ttk
from typing import cast

from thonny import running, get_runner, get_workbench
from thonny.common import InlineCommand
from thonny.languages import tr
from thonny.plugins.files import upload
from thonny.plugins.micropython import MicroPythonProxy, LocalMicroPythonProxy
from thonny.plugins.pip_gui import (
    BackendPipDialog,
    SEARCH_ON_PYPI,
    DELETE_SELECTED,
    INSTALL,
    UNINSTALL,
)


class MicroPythonPipDialog(BackendPipDialog):
    def __init__(self, master):
        self._current_temp_dir = None
        self._checkboxes = []
        super().__init__(master)
        assert isinstance(self._backend_proxy, MicroPythonProxy)

    def _create_pip_process(self, args, stderr=subprocess.STDOUT):
        return self._create_python_process(
            ["-m", "thonny.plugins.micropython.micropip"] + args, stderr=stderr
        )

    def _get_active_version(self, name):
        # Don't have dist-level information
        return None

    def _on_install_click(self):
        if self.install_button["text"] == tr(INSTALL):
            super()._on_install_click()
        elif self.install_button["text"] == tr(SEARCH_ON_PYPI):
            self.search_box.delete(0, "end")
            self.search_box.insert(
                0, "micropython pycopy " + self.current_package_data["info"]["name"]
            )
            self._on_search(None)
        else:
            raise RuntimeError(
                "Unexpected text '%s' on install button" % self.install_button["text"]
            )

    def _on_uninstall_click(self):
        if self.uninstall_button["text"] == tr(UNINSTALL):
            super()._on_uninstall_click()
        elif self.uninstall_button["text"] == tr(DELETE_SELECTED):
            self._delete_selected()
        else:
            raise RuntimeError(
                "Unexpected text '%s' on install button" % self.install_button["text"]
            )

    def _delete_selected(self):
        paths = []
        for cb in self._checkboxes:
            if cb.variable.get():
                paths.append(cb.full_path)

        if paths:
            self._delete_paths(paths)
            self._start_update_list(self.current_package_data["info"]["name"])

    def _delete_paths(self, paths):
        get_runner().send_command_and_wait(
            InlineCommand("delete", paths=paths), dialog_title=tr("Deleting"),
        )

    def _get_install_command(self):
        return ["install", "-p", self._current_temp_dir]

    def _perform_pip_action(self, action: str) -> bool:
        if self._perform_pip_action_without_refresh(action):
            self._show_instructions()  # Make the old package go away as fast as possible

            # don't know which module to show, therefore None arg
            self._start_update_list(None)

    def _perform_pip_action_without_refresh(self, action: str) -> bool:
        assert action in ["install", "advanced"]

        self._current_temp_dir = tempfile.mkdtemp()
        try:
            if super()._perform_pip_action_without_refresh(action):
                return self._upload_installed_files()
            else:
                return False
        finally:
            shutil.rmtree(self._current_temp_dir, ignore_errors=True)
            self._current_temp_dir = None

    def _upload_installed_files(self) -> bool:
        paths = []
        for (dirpath, dirnames, filenames) in os.walk(self._current_temp_dir):
            if dirpath != self._current_temp_dir:
                paths.append(dirpath)

            for filename in filenames:
                source_path = os.path.join(dirpath, filename)
                paths.append(source_path)

        if not paths:
            showerror("Error", "Did not find anything to upload from micropip target path")
            return False

        print("up", paths)
        return upload(paths, self._current_temp_dir, self._get_target_directory())

    def _create_python_process(self, args, stderr):
        proc = running.create_frontend_python_process(args, stderr=stderr)
        return proc, proc.cmd

    def _on_listbox_select_package(self, name):
        self._start_show_module_info(name)

    def _start_show_module_info(self, name):
        self._clear_info_text()
        self.command_frame.grid_remove()
        self.title_label["text"] = tr("Module") + (" '%s'" % name)
        self.title_label.grid()
        self._set_state("fetching")
        self.advanced_button.grid_remove()

        get_workbench().bind("get_module_info_response", self._complete_display_module_info, True)
        get_runner().send_command(InlineCommand("get_module_info", module_name=name))

    def _complete_display_module_info(self, msg):
        self._set_state("idle")
        self.current_package_data = {"info": {"name": msg.module_name}}
        get_workbench().unbind("get_module_info_response", self._complete_display_module_info)

        self._append_info_text(tr("Installed to:") + " ", ("caption",))
        self._append_info_text(msg["location"] + "\n")

        for cb in self._checkboxes:
            cb.destroy()
        self._checkboxes.clear()

        for item in msg["effective_items"]:
            self._append_file_checkbox(item, msg["location"])

        if msg["shadowed_items"]:
            self._append_info_text("\n")
            self._append_info_text(tr("Shadowed items (not importable):") + "\n", ("caption",))
            for item in msg["shadowed_items"]:
                self._append_file_checkbox(item, None)

        self.command_frame.grid()
        self.uninstall_button.grid()
        self.install_button["text"] = tr(SEARCH_ON_PYPI)
        self.uninstall_button["text"] = tr(DELETE_SELECTED)
        self.uninstall_button["state"] = "normal" if self._checkboxes else "disabled"
        self._select_list_item(msg.module_name)

    def _append_file_checkbox(self, full_path, context_dir):
        if context_dir:
            text = full_path[len(context_dir) :].strip("/")
        else:
            text = full_path

        if self._can_delete(full_path):
            cb = ttk.Checkbutton(self.info_text, text=text)
            var = tk.IntVar(value=1)
            cb.variable = var  # to avoid it being gc-d
            cb["variable"] = var
            cb.full_path = full_path
            self._checkboxes.append(cb)
            self.info_text.window_create("end", window=cb)
        else:
            self._append_info_text("• " + text)

        self._append_info_text("\n")

    def _can_delete(self, path):
        return not path.startswith("/usr/lib")

    def _get_target_directory(self):
        target_dir = self._backend_proxy.get_pip_target_dir()
        return target_dir

    def _read_only(self):
        return self._get_target_directory() is None

    def _show_instructions_about_existing_packages(self):
        self._append_info_text(tr("Upgrade or uninstall") + "\n", ("caption",))
        self.info_text.direct_insert(
            "end", tr("For upgrading simply install the package again.") + "\n"
        )
        self.info_text.direct_insert(
            "end", tr("For uninstalling delete corresponding files.") + "\n\n"
        )

    def _show_instructions_about_installing_from_local_file(self):
        # not supported
        pass

    def _use_user_install(self):
        return False

    def does_support_update_deps_switch(self):
        return False

    def _show_instructions_about_target(self):
        self._append_info_text(tr("Scope") + "\n", ("caption",))

        if isinstance(self._backend_proxy, LocalMicroPythonProxy):
            dir_tags = ("url",)
        else:
            dir_tags = ()

        if len(self._backend_proxy.get_lib_dirs()) == 1:
            self._append_info_text(self._get_target_directory(), dir_tags)
            self._append_info_text("\n")
        else:

            self.info_text.direct_insert(
                "end", tr("This dialog lists top-level modules from following directories:\n")
            )

            for path in self._backend_proxy.get_lib_dirs():
                self._append_info_text("• ")
                self._append_info_text(path, dir_tags)
                self._append_info_text("\n")

            self._append_info_text("\n")
            self._append_info_text(tr("New packages will be installed to") + "\n")
            self._append_info_text("• ")
            self._append_info_text(self._get_target_directory(), dir_tags)
            self._append_info_text("\n")

    def _show_read_only_instructions(self):
        self._append_info_text(tr("Not available") + "\n", ("caption",))
        self.info_text.direct_insert(
            "end", tr("Package manager is not available for this interpreter") + "\n\n",
        )

    def _tweak_search_results(self, results, query):
        if results is None:
            return results

        def get_order(item):
            name = item["name"]
            if name == query or name.startswith("micropython-") or name.startswith("pycopy-"):
                return 1
            elif "micropython" in name.lower() or "pycopy" in name.lower():
                return 2
            elif item.get("description"):
                description = item["description"]
                if "micropython" in description.lower() or "pycopy" in description.lower():
                    return 3

            return 4

        return sorted(results, key=get_order)


class LocalMicroPythonPipDialog(MicroPythonPipDialog):
    def _get_install_command(self):
        return ["install", "-p", self._get_target_directory()]

    def _upload_installed_files(self) -> bool:
        "nothing to do -- micropip installed files directly to the right directory"

    def _delete_paths(self, paths):
        # assuming all files are listed if their directory is listed
        for path in reversed(sorted(paths, key=len, reverse=True)):
            os.remove(path)