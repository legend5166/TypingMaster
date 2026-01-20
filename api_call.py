from ctypes import windll, c_int, c_void_p, c_long, c_uint
import ctypes.wintypes 
# from ctypes import wintypes
import os
from utility import get_path, BASE_DIR

user32 = windll.user32
# 根据类名或窗口标题取窗口句柄
FindWindowW = user32.FindWindowW
FindWindowW.argtypes = (ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR)
FindWindowW.restype = ctypes.wintypes.HWND
# 将指定句柄的窗口置顶
SetForegroundWindow = user32.SetForegroundWindow
SetForegroundWindow.argtypes = (ctypes.wintypes.HWND,)
# 使用 ShowWindow 函数将窗口显示出来
ShowWindow = user32.ShowWindow
ShowWindow.argtypes = (ctypes.wintypes.HWND, c_int)
SW_SHOWNORMAL = 1


# title = 'DK-批量文件重命名'
# class_name = 'wxWindowNR'

def set_foreground_window_by_title(title=None, class_name=None):
	# 将指定标题的窗口置于前台。
	hwnd = FindWindowW(class_name, title)
	# print(hwnd)
	if hwnd:
		SetForegroundWindow(hwnd)
		ShowWindow(hwnd, SW_SHOWNORMAL)

# 设置活动区域通知
NotifyWinEvent = user32.NotifyWinEvent
NotifyWinEvent.argtypes = [c_uint, c_void_p, c_long, c_long]
NotifyWinEvent.restype = None
EVENT_OBJECT_LIVEREGIONCHANGED = 0x8019
#An object that is part of a live region has changed. A live region is an area of an application that changes frequently and/or asynchronously.
OBJID_CLIENT = -4
CHILDID_SELF = 0

def live_region_changed(hwnd):
	NotifyWinEvent(EVENT_OBJECT_LIVEREGIONCHANGED, hwnd, OBJID_CLIENT, CHILDID_SELF)

# UIA Notification

HRESULT = ctypes.c_long
HWND = ctypes.wintypes.HWND
dll_name = "uianotify64.dll" if ctypes.sizeof(ctypes.c_void_p) == 8 else "uianotify32.dll"
dll_path = get_path(dll_name, 'api', must_exist=True)
uianotify = None
if dll_path is  not None:
	os.add_dll_directory(os.path.dirname(dll_path))
	uianotify = ctypes.WinDLL(dll_name)

if uianotify is not None:
	uianotify.UiaAreClientsListening.restype = ctypes.c_int
	uianotify.UiaAreClientsListening.argtypes = []
	uianotify.UiaRaiseNotificationFromHwnd.restype = HRESULT
	uianotify.UiaRaiseNotificationFromHwnd.argtypes = [
		HWND, ctypes.c_int, ctypes.c_int,
		ctypes.c_wchar_p, ctypes.c_wchar_p,
		ctypes.c_wchar_p, ctypes.c_uint
	]

class NotificationKind:
	ItemAdded = 0
	ItemRemoved = 1
	ActionCompleted = 2
	ActionAborted = 3
	Other = 4


class NotificationProcessing:
	ImportantAll = 0
	ImportantMostRecent = 1
	All = 2
	MostRecent = 3
	CurrentThenMostRecent = 4


def notify_from_wx(frame, text, activity_id="wxApp"):
	hwnd = HWND(frame.GetHandle())
	buf = ctypes.create_unicode_buffer(512)
	try:
		hr = uianotify.UiaRaiseNotificationFromHwnd(
			hwnd,
			# NotificationKind.Other,
			NotificationKind.ActionCompleted,
			NotificationProcessing.ImportantAll,
			text,
			activity_id,
			buf,
			len(buf)
		)
		# if hr == 0:
			# print("Notification raised successfully.")
		# elif hr == 1:
			# print("No clients listening. Info:", buf.value)
		# else:
			# print(f"Failed: HRESULT=0x{hr & 0xFFFFFFFF:08X} {buf.value}")
	except Exception:
		pass

