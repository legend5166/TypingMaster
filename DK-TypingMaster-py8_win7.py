import wx
import BaseUI
import dialog
import logging, sys
import utility
import showImage
import api_call
from threading import Thread
from datetime import datetime
import webbrowser
import random
if sys.getwindowsversion().major >= 10:
	try:
		from  neural import NeuralSynthesizer
		imported_neural = True
	except:
		imported_neural = False
else:
	imported_neural = False


logging.basicConfig(filename=utility.get_path('typing_master.log', 'config', False), level=logging.ERROR,
	format='%(asctime)s - %(levelname)s - %(message)s') # - %(funcName)s - Line:%(lineno)d')
logger = logging.getLogger()
logging.captureWarnings(True)
def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
	logger.error("Uncaught exception\n",
				exc_info=(exc_type, exc_value, exc_traceback))
	# 将错误继续发送给默认异常抛出
	# sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = log_uncaught_exceptions


class TypingMaster(BaseUI.TypingMaster):
	def __init__(self, *args, **kwds):
		super().__init__(*args, **kwds)
		self.imported_neural = imported_neural
		self.starts_time = None
		self.synth = None
		self.statistic_text = None #'还没有统计数据'
		self.processing = False
		self.explain_data = {}
		self.wrong_typing = []
		self.counter_char = self.counter_incorrect_char = self.incorrect_typing = self.correct_typing = 0
		self.tc_show_last_point = True # first does not need \n
		self.SetTreeCtrl()
		self.single_timing = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.OnSingleInput, self.single_timing)
		self.waiting_timing = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.OnWaitingTiming, self.waiting_timing)
		self.tc_typing.Bind(wx.EVT_CHAR_HOOK, self.OnTcTypingHook)
		self.tree.Bind(wx.EVT_CONTEXT_MENU, self.OnTreeContext)
		# self.tree.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnTreeContext)
		wx.CallAfter(self.InitData)

	def OnTreeContext(self, evt):
		selected_item = self.tree.GetSelection()
		if not selected_item.IsOk(): return
		self.is_scheme_item = False
		# if selected_item == self.tree.GetRootItem(): return
		self.selected_text = self.tree.GetItemText(selected_item)
		menu = wx.Menu()
		if  self.tree.GetItemParent(selected_item) != self.tree.GetRootItem():
			parent_item = self.tree.GetItemParent(selected_item)
			self.parent_text = self.tree.GetItemText(parent_item)
			self.is_scheme_item = True
			edit = menu.Append(wx.ID_EDIT, '编辑(&E)')
			delete = menu.Append(wx.ID_DELETE, '删除(&D)')
			view = menu.Append(wx.ID_PREVIEW, '预览(&V)')
			self.Bind(wx.EVT_MENU, self.OnEditContext, edit)
			self.Bind(wx.EVT_MENU, self.OnDeleteContext, delete)
			self.Bind(wx.EVT_MENU, self.OnViewContext, view)

		add = menu.Append(wx.ID_ADD, '新建(&A)')
		self.Bind(wx.EVT_MENU, self.OnAddContext, add)
		self.tree.PopupMenu(menu)
		menu.Destroy()

	def OnAddContext(self, evt):
		dlg = dialog.EditSchemeDialog(self, title = '新建', mode = 'new')
		item = self.tree.GetSelection()
		if  not item.IsOk(): return
		parent_item = self.tree.GetItemParent(item) if self.is_scheme_item else item
		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.combo_box_name.GetValue()
			self.tree.AppendItem(parent_item, name)
			content = dlg.tc_content.GetValue()
			data = content.split()
			self.scheme_keys[self.parent_text].append(name)
			self.scheme_data[self.parent_text][name] = data
			utility.dump_shelve_data(scheme = self.scheme_data, scheme_keys = self.scheme_keys)

		dlg.Destroy()

	def OnEditContext(self, evt):
		if not self.is_scheme_item: return
		data = self.scheme_data[self.parent_text][self.selected_text]
		dlg = dialog.EditSchemeDialog(self, title = f'编辑 - {len(data)} 个字/词', mode = 'edit', name_content=[self.selected_text], new_content=data)
		if dlg.ShowModal() == wx.ID_OK:
			self.scheme_data[self.parent_text][dlg.scheme_name] = dlg.scheme_content
			if dlg.scheme_name not in self.scheme_keys[self.parent_text]:
				del self.scheme_data[self.parent_text][self.selected_text]
				index = self.scheme_keys[self.parent_text].index(self.selected_text)
				self.scheme_keys[self.parent_text][index] = dlg.scheme_name
				self.tree.SetItemText(self.tree.GetSelection(), dlg.scheme_name)

			utility.dump_shelve_data(scheme = self.scheme_data, scheme_keys = self.scheme_keys)
		dlg.Destroy()

	def OnDeleteContext(self, evt):
		if not self.is_scheme_item: return
		dlg = wx.MessageDialog(self, '确认删除当前练习方案吗？', f'确认删除"{self.selected_text}"',wx.YES_NO|wx.CANCEL|wx.NO_DEFAULT|wx.ICON_QUESTION)
		if dlg.ShowModal() == wx.ID_YES:
			try:
				item = self.tree.GetSelection()
				self.tree.Delete(item)
				del self.scheme_data[self.parent_text][self.selected_text]
				self.scheme_keys[self.parent_text].remove(self.selected_text)
				utility.dump_shelve_data(scheme = self.scheme_data, scheme_keys = self.scheme_keys)
			except:
				pass

		dlg.Destroy()


	def OnViewContext(self, evt):
		if self.is_scheme_item:
			data = self.scheme_data.get(
				self.parent_text).get(self.selected_text)
			dlg = dialog.EditSchemeDialog(self, 
				title = f'预览 - {len(data)} 个字/词',
				name_content=(self.selected_text,),
				new_content= data,
				mode = 'view'
				)
			dlg.ShowModal()
			dlg.Destroy()

	def InitData(self):
		self.map_submenu_to_enum = {utility.WordExplain.ON: self.frame_menubar.explain_on,
				utility.WordExplain.OFF: self.frame_menubar.explain_off,
				utility.WordExplain.AUTO: self.frame_menubar.explain_auto}
		data = utility.load_shelve_data('scheme', 'preferences')
		self.scheme_data = data['scheme']
		self.preferences = data['preferences']
		self.explain_mode = utility.WordExplain(self.preferences.get('explain_mode', 1))
		self.map_submenu_to_enum[self.explain_mode].Check(True)
		self.waiting_time = self.preferences.get('waiting_time', 10)
		self.speak_mode = self.preferences.get('speak_mode', 0)
		self.voice = self.preferences.get('voice', "Microsoft Xiaoxiao (Natural) - Chinese (Simplified, China)")
		self.rate  = self.preferences.get('rate', 80)
		self._rate = utility.convert_speak_parameter_to_string((self.rate - 50) *4)
		self.pitch = self.preferences.get('pitch', 50)
		self._pitch = utility.convert_speak_parameter_to_string(self.pitch - 50)
		self.volume = self.preferences.get('volume', 80)
		self._volume = utility.convert_speak_parameter_to_string(self.volume - 80)
		if self.speak_mode == 1:
			if imported_neural:
				self.synth = NeuralSynthesizer()
				self.SpeakText = self._SpeakWithNeural
		elif self.speak_mode == 0:
			self.SpeakText  = self._SpeakWithLiveRegion
			# self.synth = None
		elif self.speak_mode == 2:
			self.speak_api = utility.SRAPI('ZDSRAPI.dll')
			self.SpeakText = self._SpeakWithSpeakAPI
		elif self.speak_mode ==3:
			self.speak_api = utility.SRAPI('nvdaControllerClient.dll')
			self.SpeakText = self._SpeakWithSpeakAPI


	def SpeakText(self, text, voice, rate, pitch, volume):
		pass

	def _SpeakWithSpeakAPI(self, text, **kwds):
		if self.speak_api is not None:
			self.speak_api.speak(text)

	def _SpeakWithLiveRegion(self, text, **kwds):
		self.label_notification.SetLabel(text)
		api_call.live_region_changed(self.label_notification.GetHandle())

	def _SpeakWithNeural(self, text, **kwds):
		if self.synth.is_speaking: self.synth.stop()
		self.synth.speak(text,**kwds)

	def SetTreeCtrl(self):
		self.scheme_keys = utility.load_shelve_data('scheme_keys')
		root = self.tree.AddRoot('练习方案')
		if self.scheme_keys:
			for k,v in self.scheme_keys.items():
				category = self.tree.AppendItem(root, k)
				for name in v:
					self.tree.AppendItem(category, name)
		self.tree.ExpandAll()

	def OnStartBTN(self, event):
		if self.processing:
			time_span = (datetime.now() - self.starts_time).seconds
			self.processing  = False
			if self.waiting_timing.IsRunning():
				self.waiting_timing.Stop()
			self.button_start.SetLabel('开始(&S)')
			self.ShowStatisticInfo(time_span)
			return
		# self.counter_char = self.counter_incorrect_char = self.incorrect_typing = self.correct_typing = 0
		item = self.tree.GetSelection()
		if item:
			root_item = self.tree.GetRootItem()
			if item == root_item: return
			parent_item = self.tree.GetItemParent(item)
			if parent_item == root_item: return
			name = self.tree.GetItemText(item)
			parent_name = self.tree.GetItemText(parent_item)
			# self.scheme_data = utility.load_shelve_data('scheme')
			self.exercise = self.scheme_data.get(parent_name, {}).get(name)
			if self.exercise:
				self.counter_char = self.counter_incorrect_char = self.incorrect_typing = self.correct_typing = 0
				self.wrong_typing = []
				self.exercise = random.sample(self.exercise, len(self.exercise))
				self.tc_typing.SetFocus()
				self.button_start.SetLabel('结束(&S)')
				self.tc_show.SetValue('')
				self.frame_statusbar.SetStatusText(f'共{len(self.exercise)}', 2)
				if not self.explain_data: self.explain_data = utility.load_shelve_data('explain')
				self.ExtractWord()
				self.processing = True
				self.starts_time = datetime.now()
			else:
				wx.MessageBox('该方案下还没有数据哦', '信息')

	def ExtractWord(self):
		self.word = self.exercise.pop()
		self.word_len = len(self.word)
		self.label_display.SetLabel(self.word)
		if self.explain_mode == utility.WordExplain.ON:
			self.speak_text = ','.join((self.word, ','.join(map(lambda i:self.explain_data.get(i,i), self.word))))
		elif self.explain_mode == utility.WordExplain.OFF:
			self.speak_text = self.word
		elif self.explain_mode == utility.WordExplain.AUTO:
			if self.word_len > 2:
				self.speak_text = self.word
			else:# 三字以上不解释
				self.speak_text = ','.join((self.word, ','.join(map(lambda i:self.explain_data.get(i,i), self.word))))
		# self.SpeakWord(self.speak_text)
		self.SpeakText(self.speak_text, voice=self.voice, rate = self._rate, pitch=self._pitch, volume=self._volume)
		if  self.waiting_time > 0:
			self.waiting_timing.Stop()
			self.waiting_timing.StartOnce(self.waiting_time * 1000)


	def SpeakWord(self, word):
		self.label_notification.SetLabel(word)
		api_call.live_region_changed(self.label_notification.GetHandle())

	def OnTypingText(self, evt):
		if not self.processing:
			self.tc_typing.SetValue('')
			evt.Skip()
			return
		text = evt.GetString()
		if not text:
			return
		if text == ' ':
			self.tc_typing.SetValue('')
			return
		self.single_timing.StartOnce(20)

	def OnWaitingTiming(self, evt):
		if self.processing:
			utility.play_sound(utility.snd_incorrect)
			self.tc_show.AppendText(f'{self.word} [_] \n' if self.tc_show_last_point else f'\n{self.word } [_] \n')
			self.tc_show_last_point = True # is \n
			self.counter_incorrect_char += self.word_len
			self.incorrect_typing += 1
			self.wrong_typing.append((self.word, '_'))
			self.tc_typing.SetValue('')
			self.frame_statusbar.SetStatusText(f'已完成{self.correct_typing + self.incorrect_typing};', 0)
			self.frame_statusbar.SetStatusText(f'正确 {self.correct_typing}; 错误 {self.incorrect_typing}', 1)
			if self.exercise:
				self.ExtractWord()
			else:
				self.processing = False
				time_span = (datetime.now() - self.starts_time).seconds
				self.button_start.SetLabel('开始(&S)')
				self.ShowStatisticInfo(time_span)


	def OnSingleInput(self, evt):
		# event for self.single_timing timer
		text = self.tc_typing.GetValue()
		if text == self.word:
			self.tc_show.AppendText(';'.join((self.word, ' ')))
			self.tc_show_last_point = False # not \n
			# self.counter_incorrect_char += 1
			self.counter_char += self.word_len
			self.correct_typing += 1
		elif self.word.startswith(text):
			# 非一次性上屏，等待用户输入剩余部分
			return
		else:
			utility.play_sound(utility.snd_incorrect)
			self.tc_show.AppendText(f'{self.word} [{text}] \n' if self.tc_show_last_point else f'\n{self.word } [{text}] \n')
			self.tc_show_last_point = True # is \n
			self.counter_incorrect_char += self.word_len
			self.incorrect_typing += 1
			self.wrong_typing.append((self.word, text))

		self.tc_typing.SetValue('')
		self.frame_statusbar.SetStatusText(f'已完成{self.correct_typing + self.incorrect_typing};', 0)
		self.frame_statusbar.SetStatusText(f'正确 {self.correct_typing}; 错误 {self.incorrect_typing}', 1)
		if self.exercise:
			self.ExtractWord()
		else:
			time_span = (datetime.now() - self.starts_time).seconds
			self.button_start.SetLabel('开始(&S)')
			self.processing = False
			if self.waiting_timing.IsRunning(): self.waiting_timing.Stop()
			self.ShowStatisticInfo(time_span)

	def ShowStatisticInfo(self, time_span):
		self.label_display.SetLabel('输入')
		if (self.correct_typing + self.incorrect_typing) == 0:
			return
		utility.play_sound(utility.snd_complete)
		dlg = dialog.TypingStatisticDialog(self)
		if self.wrong_typing:
			wrong_text = '本次输入错误的字词有：\n' + '\n'.join(map(lambda i: f'{i[0]} [{i[1]}]', self.wrong_typing))
		else:
			wrong_text = ''
			dlg.button_OK.SetLabel('确定')
		self.statistic_text = '\n'.join((f'本次练习共 {self.correct_typing + self.incorrect_typing} 个字/词。',
			f'正确 {self.correct_typing} 个。',
					 f'错误 {self.incorrect_typing} 个。',
			f'正确率 {round(self.correct_typing / (self.correct_typing + self.incorrect_typing),4) * 100}%。 ',
			f'共计 {self.counter_char + self.counter_incorrect_char} 字， 用时 {utility.convert_seconds(time_span)}。',
			f'平均打字速度： {round((self.counter_char + self.counter_incorrect_char) / (time_span / 60),2)} 字/分钟。',
			f'正确输入 {self.counter_char} 字。',
			f'有效输入平均速度： {round(self.counter_char / (time_span / 60),2)} 字/分钟。',
			wrong_text,
			))
		dlg.tc_display.SetValue(self.statistic_text)
		if dlg.ShowModal() == wx.ID_OK:
			dlg.Destroy()
			if not self.wrong_typing: return
			self.ShowAddIncorrectDialog()
		else:
			dlg.Destroy()


	def OnTcTypingHook(self, evt):
		if self.processing:
			keycode = evt.GetKeyCode()
			modifiers = evt.GetModifiers()
			if keycode == wx.WXK_TAB and modifiers == 0 or modifiers == 2 and keycode == 73:
				# self.SpeakWord(self.speak_text)
				self.SpeakText(self.speak_text, voice=self.voice, rate = self._rate, pitch=self._pitch, volume=self._volume)
			elif keycode == 13 and modifiers == 0:
				utility.play_sound(utility.snd_incorrect)
				self.tc_show.AppendText(f'{self.word} [_] \n' if self.tc_show_last_point else f'\n{self.word } [_]] \n')
				self.tc_show_last_point = True # is \n
				self.incorrect_typing += 1
				self.counter_incorrect_char += 1
				self.wrong_typing.append((self.word, '_'))
				self.tc_typing.SetValue('')
				self.frame_statusbar.SetStatusText(f'已完成{self.correct_typing + self.incorrect_typing};', 0)
				self.frame_statusbar.SetStatusText(f'正确 {self.correct_typing}; 错误 {self.incorrect_typing}', 1)
				if self.exercise:
					self.ExtractWord()
				else:
					time_span = (datetime.now() - self.starts_time).seconds
					self.processing = False
					if self.waiting_timing.IsRunning(): self.waiting_timing.Stop()
					self.button_start.SetLabel('开始(&S)')
					self.ShowStatisticInfo(time_span)
			else:
				evt.Skip()
		else:
			evt.Skip()

	def OnStatisticReport(self, evt):
		dlg = dialog.TypingStatisticDialog(self)
		dlg.tc_display.SetValue(self.statistic_text if self.statistic_text else '还没有统计数据')
		if dlg.ShowModal() == wx.ID_OK:
			dlg.Destroy()
			self.ShowAddIncorrectDialog()
		else:
			dlg.Destroy()

	def ShowAddIncorrectDialog(self):
		scheme_names = self.scheme_keys.get('自定义',[])
		edit_dlg = dialog.EditSchemeDialog(self, 
			name_content = scheme_names,
			new_content=list(map(lambda i: i[0], self.wrong_typing)))
		if edit_dlg.ShowModal() == wx.ID_OK:
			data = self.scheme_data['自定义'].get(edit_dlg.scheme_name, [])
			data.extend(edit_dlg.scheme_content)
			self.scheme_data['自定义'][edit_dlg.scheme_name] = data
			if edit_dlg.scheme_name not in self.scheme_keys['自定义']:
				self.scheme_keys['自定义'].append(edit_dlg.scheme_name)
				self.tree.AppendItem(self.GetTreeItemByLabel('自定义'), edit_dlg.scheme_name)
			utility.dump_shelve_data(scheme = self.scheme_data, scheme_keys = self.scheme_keys)

		edit_dlg.Destroy()

	def GetTreeItemByLabel(self,label):
		child, cookie = self.tree.GetFirstChild(self.tree.GetRootItem())
		while child.IsOk():
			if self.tree.GetItemText(child) == label:
				return child
			child = self.tree.GetNextSibling(child)
		return wx.TreeItemId()

	def OnExtremeSpeed(self, evt):
		dlg = dialog.MeasureSpeedDialog(self)
		dlg.Show()
		# dlg.Destroy()

	def OnWordExplain(self, evt):
		menu_item = self.GetMenuBar().FindItemById(evt.GetId())
		for e, submenu in self.map_submenu_to_enum.items():
			if submenu == menu_item:
				self.explain_mode = e

		# item_label = menu_item.GetItemLabelText()
		# if item_label == '开':
			# self.explain_mode = utility.WordExplain.ON
		# elif item_label == '关':
			# self.explain_mode = utility.WordExplain.OFF
		# elif item_label == '自动':
			# self.explain_mode = utility.WordExplain.AUTO
		self.preferences['explain_mode'] = self.explain_mode.value
		utility.dump_shelve_data(preferences=self.preferences)

	def OnPreferences(self, evt):
		if imported_neural and (not self.synth): self.synth = NeuralSynthesizer()
		dlg = dialog.MyPreferencesDialog(self,waiting_time=self.waiting_time, speak_mode=self.speak_mode,
			voices = self.synth.get_voices() if self.synth else [],
			rate =self.rate,
			pitch = self.pitch,
			volume=self.volume,
			)
		if dlg.ShowModal() == wx.ID_OK:
			self.waiting_time = int(dlg.combo_box_time.GetSelection())
			self.speak_mode = dlg.choice_speak_mode.GetSelection()
			self.preferences.update({
			'waiting_time': self.waiting_time,
			'speak_mode':self.speak_mode,
			})
			if self.speak_mode == 0:
				self.SpeakText = self._SpeakWithLiveRegion
			elif self.speak_mode == 1:
				if imported_neural:
					self.synth = NeuralSynthesizer()
					self.SpeakText = self._SpeakWithNeural
					self.voice = dlg.choice_voice.GetStringSelection()
					self.rate = dlg.slider_rate.GetValue()
					self.pitch = dlg.slider_pitch.GetValue()
					self.volume = dlg.slider_volume.GetValue()
					self.preferences.update({
						'voice': self.voice,
						'rate': self.rate,
						'pitch': self.pitch,
						'volume': self.volume,
					})
			elif self.speak_mode ==2:
				self.speak_api = utility.SRAPI('ZDSRAPI.dll', error_msg=True)
				self.SpeakText = self._SpeakWithSpeakAPI
			elif self.speak_mode == 3:
				self.speak_api = utility.SRAPI('nvdaControllerClient.dll', error_msg=True)
				self.SpeakText = self._SpeakWithSpeakAPI

			utility.dump_shelve_data(preferences = self.preferences)
		dlg.Destroy()

	def OnExit(self, evt):
		self.Destroy()

	def OnWubiDialog(self, evt):
		dlg = dialog.WuBiSearchDialog(self)
		if dlg.ShowModal() == wx.ID_OK:
			pass
		dlg.Destroy

	def OnHanziDialog(self, evt):
		dlg = dialog.HanZiSearchDialog(self)
		if dlg.ShowModal() ==wx.ID_OK:
			pass
		dlg.Destroy

	def OnWechat(self, evt):
		img_path = utility.get_path('wechat.png')
		if img_path is not None:
			img = wx.Image(img_path, wx.BITMAP_TYPE_PNG)
			img_window = showImage.ImageFrame(img, parent=self, title='微信赞赏')
			img_window.Raise()
			img_window.Show()

	def OnAlipay(self, evt):
		img_path = utility.get_path('alipay.jpg')
		if img_path is not None:
			img = wx.Image(img_path, wx.BITMAP_TYPE_JPEG)
			img_window = showImage.ImageFrame(img, parent=self, title='支付宝赞赏')
			img_window.Raise()
			img_window.Show()

	def OnQQGroupNumber(self, evt):
		info = f'大可小筑\n951516588\n加群口令：\n666\n'
		dlg = wx.MessageDialog(self, info, f'大可小筑 951516588', wx.OK|wx.CANCEL|wx.ICON_QUESTION)
		dlg.SetOKLabel('复制群号到剪贴板')
		if dlg.ShowModal() == wx.ID_OK:
			if wx.TheClipboard.IsOpened() or wx.TheClipboard.Open():
				wx.TheClipboard.SetData(wx.TextDataObject(info))
				wx.TheClipboard.Flush()
				wx.TheClipboard.Close()
		dlg.Destroy()

	def OnQQLink(self, evt):
		url = 'http://qm.qq.com/cgi-bin/qm/qr?_wv=1027&k=3GO65fdFxsmfavpUR6NjC3IZJ21-2Tmv&authKey=RmacQwC5l6%2FSmdbmisRSJoGNWbMxXqGXAtcqx%2BBhiL%2FeAbe8t6s%2B4Vu7pmDBx5gv&noverify=0&group_code=951516588'
		webbrowser.open(url)

	def OnQQQRCode(self, evt):
		img_path = utility.get_path('gQRCode.png')
		if img_path is not None:
			img = wx.Image(img_path, wx.BITMAP_TYPE_PNG)
			img_window = showImage.ImageFrame(img, parent=self, title='大可小筑加群二维码')
			img_window.Center()
			img_window.Maximize()
			img_window.Raise()
			img_window.Show()


class MyApp(wx.App):
	def OnInit(self):
		self.single_instance_checker = wx.SingleInstanceChecker('dake_typing_master')
		if self.single_instance_checker.IsAnotherRunning():
			api_call.set_foreground_window_by_title('DK-打字通')
			return False

		# logging.basicConfig(filename=utility.get_path('typing_master.log', 'config', False), level=logging.ERROR,
							# format='%(asctime)s - %(levelname)s - %(message)s') # - %(funcName)s - Line:%(lineno)d')
		# sys.excepthook = self.log_uncaught_exceptions

		self.locale = wx.Locale(wx.LANGUAGE_DEFAULT)
		self.locale = wx.Locale(wx.LANGUAGE_CHINESE_SIMPLIFIED)
		self.frame = TypingMaster(None, wx.ID_ANY, "")
		self.SetTopWindow(self.frame)
		self.frame.Show()
		return True

	def log_uncaught_exceptions(self, exc_type, exc_value, exc_traceback):
		# 将未捕获的异常记录到日志文件
		logger.error("Uncaught exception\n",
					exc_info=(exc_type, exc_value, exc_traceback))
		# 将错误继续发送给默认异常抛出
		# sys.__excepthook__(exc_type, exc_value, exc_traceback)

if __name__ == "__main__":
	app = MyApp(True, filename=utility.get_path('output.log', '', False))
	# app = MyApp(0)
	app.MainLoop()
