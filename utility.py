import pickle
import shelve
import os.path
import ctypes
from os import mkdir
from enum import Enum
from winsound import PlaySound, SND_FILENAME, SND_ASYNC

class WordExplain(Enum):
	ON = 1
	OFF = 2
	AUTO = 3


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
snd_incorrect = os.path.join(BASE_DIR, 'effects', 'incorrect.wav')
snd_complete = os.path.join(BASE_DIR, 'effects', 'complete.wav')

def get_path(filename, dir_name= 'IMG', must_exist = True):
	_path = os.path.join(BASE_DIR, dir_name, filename)
	if not must_exist: return _path
	if os.path.exists(_path):
		return _path
	return None

def play_sound(sound):
	PlaySound(sound, SND_FILENAME|SND_ASYNC)

def verify_dir(dirname,base_dir=BASE_DIR):
	path = os.path.join(base_dir, dirname)
	if not os.path.exists(path):
		mkdir(path)
	return path

config_dir = verify_dir('config')

def make_exercise_scheme_pickle():
	from exercise import scheme
	# print(type(scheme))
	# print(len(scheme))
	with open(os.path.join(config_dir, 'scheme.data'), 'wb') as f:
		pickle.dump(scheme, f)


def load_pickle_data(pickle_file):
	config_path = verify_dir('config')
	file_path = os.path.join(config_dir, pickle_file)
	if not os.path.exists(file_path):
		return

	try:
		with open(file_path, 'rb') as f:
			data = pickle.load(f)
	except:
		return

	return data

def convert_seconds(seconds):
	minutes, seconds=divmod(seconds, 60)
	minutes = f'{minutes}分' if minutes else ''
	return f'{minutes} {seconds}秒'

def load_shelve_data(*key):
	config_path = verify_dir('config')
	shelve_path = os.path.join(config_dir, 'user')
	with shelve.open(shelve_path) as db:
		if len(key) == 1:
			data = db.get(key[0], {})
		# return data
		else:
			data = {}
			for k in key:
				data[k] = db.get(k, {})
	return data


def dump_shelve_data(**kwds):
	config_path = verify_dir('config')
	shelve_path = os.path.join(config_dir, 'user')
	with shelve.open(shelve_path) as db:
		for k,v in kwds.items():
			db[k] = v

def convert_speak_parameter_to_string(value:int) -> str:
	string = f'{value}%'
	if not string.startswith('-'):
		string = '+' + string
	return string

class SRAPI:
	def __new__(cls, *args, **kwds):
		api_name = args[0]
		error_msg = kwds.get('error_msg', False)
		if (api_path:=get_path(api_name, 'API')) is None:
			if error_msg: ctypes.windll.user32.MessageBoxW(0, f"找不到 {api_name} ", "文件不存在", 0)
			return None
		try:
			api = ctypes.windll.LoadLibrary(api_path)
		except Exception as e:
			if error_msg: ctypes.windll.user32.MessageBoxW(0, f"{str(e)}", f"加载 {api_name} 时发生错误", 0)
			return None
		if (name:=api_name.lower()).startswith('zdsr'):
			res = api.InitTTS(0,None, True)
			if res !=0:
				if error_msg: 	ctypes.windll.user32.MessageBoxW(0, "初始化错误", "版本不匹配", 0)
				return None
		elif name.startswith('nvda'):
			res = api.nvdaController_testIfRunning()
			if res != 0:
				errorMessage = str(ctypes.WinError(res))
				if error_msg: ctypes.windll.user32.MessageBoxW(0, f"Error: {errorMessage}", "加载nvdaControllerClient 失败，可能nvda没有运行", 0)
				return None

		instance = super(SRAPI, cls).__new__(cls)
		instance.api = api
		instance.sr_name = name[:4]
		return instance

	def __init__(self, api_name, error_msg=False):
		pass

	def speak(self, text):
		if self.sr_name == 'zdsr':
			self.api.Speak(text, True)
		elif self.sr_name == 'nvda':
			self.api.nvdaController_speakText(text)



if __name__ == '__main__':
	data = load_shelve_data('preferences')
	# print(data)
	# print(convert_seconds(353))
