import wx

class ImageFrame(wx.Frame):
	"""Frame class that displays an image."""
	def __init__(self, image, parent=None, id=-1,	
				 pos=wx.DefaultPosition, 
				 title='Show Image'):
		"""Create a Frame instance and display image."""

		temp = image.ConvertToBitmap()							 
		size = temp.GetWidth(), temp.GetHeight()				
		wx.Frame.__init__(self, parent, id, title, pos, size)	
		self.bmp = wx.StaticBitmap(parent=self, bitmap=temp)	 

	def Destroy(self):
#		print('exit')
		return super().Destroy()
 
class App(wx.App):
	"""Application class."""
	def OnInit(self):
		image = wx.Image(r'IMG\小姐姐.jpg', wx.BITMAP_TYPE_JPEG)
		self.frame = Frame(image)
		self.frame.Show() 
		self.SetTopWindow(self.frame) 
		return True 
def main():
	app = App()		 
	app.MainLoop()

if __name__ == '__main__':
	 main()