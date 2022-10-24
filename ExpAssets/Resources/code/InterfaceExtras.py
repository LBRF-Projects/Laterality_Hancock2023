__author__ = "Austin Hurst"

from klibs import P
from klibs.KLBoundary import BoundaryInspector, RectangleBoundary, CircleBoundary
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS
from klibs.KLCommunication import message
from klibs.KLUserInterface import ui_request, key_pressed, get_clicks, mouse_clicked
from klibs.KLUtilities import pump, show_mouse_cursor, hide_mouse_cursor, mouse_pos, clip
from klibs.KLUtilities import line_segment_len as lsl
from klibs.KLResponseCollectors import Response

import random
import time
import sdl2

MED_GREY = (128, 128, 128, 255)
LIGHT_GREY = (192, 192, 192, 255)
TRANSLUCENT_GREY = (192, 192, 192, 64)
TRANSLUCENT_BLUE = (0, 0, 128, 128)


class Button(object):
    
    def __init__(self, msg, width, height=None, registration=5, location=None):
        
        self.width = width
        self.height = height if height else width
        self.hover = kld.Rectangle(self.width, self.height, fill=TRANSLUCENT_GREY)
        self.msg = msg
        
        self.__registration = registration
        self.__location = location if location else P.screen_c
        self.__init_bounds()
    
    
    def __init_bounds(self):
        if self.registration in [7, 4, 1]:
            self.x_offset = self.width // 2
        elif self.registration in [9, 6, 3]:
            self.x_offset = -self.width // 2
        else:
            self.x_offset = 0   
        if self.registration in [7, 8, 9]:
            self.y_offset = self.height // 2
        elif self.registration in [1, 2, 3]:
            self.y_offset = -self.height // 2
        else:
            self.y_offset = 0       

        self.midpoint = (self.location[0]+self.x_offset, self.location[1]+self.y_offset)
        self.x1 = self.midpoint[0] - self.width//2
        self.y1 = self.midpoint[1] - self.height//2
        self.x2 = self.midpoint[0] + self.width//2
        self.y2 = self.midpoint[1] + self.height//2
        self.bounds = RectangleBoundary("button", (self.x1, self.y1), (self.x2, self.y2))
        
        
    def draw(self):
        blit(self.msg, 5, self.midpoint)
        mp = mouse_pos()
        if self.bounds.within(mp):
            blit(self.hover, 5, self.midpoint)
        
    def listen(self, queue):
        return mouse_clicked(within=self.bounds, queue=queue)
                
    @property
    def location(self):
        return self.__location
        
    @location.setter
    def location(self, loc):
        self.__location = loc
        self.__init_bounds()
        
    @property
    def registration(self):
        return self.__registration
        
    @registration.setter
    def registration(self, reg):
        self.__registration = reg
        self.__init_bounds()



class LikertType(BoundaryInspector):

    def __init__(self, first, last, width, height, style, registration=None, location=None):

        BoundaryInspector.__init__(self)

        self.range = range(first, last+1, 1)
        self.count = len(self.range)
        self.response = None
        
        self.height = height
        self.width = width
        self.circle_size = self.height
        self.gap = (width - self.circle_size * self.count) / (self.count - 1)
        
        self._location = location if location else P.screen_c
        self._registration = registration if registration else 5
        self._init_bounds()

        numlist = []
        for num in self.range:
            num_txt = message("{0}".format(num), style, blit_txt=False)
            numlist.append((num, num_txt))
        self.numbers = dict(numlist)

        self.selected = kld.Ellipse(self.circle_size-4, fill=TRANSLUCENT_GREY)
        self.mouseover = self.selected#kld.Annulus(self.circle_size-4, 6, fill=MED_GREY)

    def _init_bounds(self):
        if self.registration in [7, 4, 1]:
            self.x_offset = self.width // 2
        elif self.registration in [9, 6, 3]:
            self.x_offset = -self.width // 2
        else:
            self.x_offset = 0   
        if self.registration in [7, 8, 9]:
            self.y_offset = self.height // 2
        elif self.registration in [1, 2, 3]:
            self.y_offset = -self.height // 2
        else:
            self.y_offset = 0       

        self.midpoint = (
            self.location[0] + self.x_offset, self.location[1] + self.y_offset
        )
        self.x1 = self.midpoint[0] - self.width // 2
        self.y1 = self.midpoint[1] - self.height // 2
        self.x2 = self.midpoint[0] + self.width // 2
        self.y2 = self.midpoint[1] + self.height // 2

        for num in self.range:
            pos = self._num_to_pos(num)
            bounds = CircleBoundary(str(num), pos, (self.circle_size * 0.6))
            self.add_boundary(bounds)
    
    def _num_to_pos(self, num):
        n = self.range.index(num)
        x_pos = self.x1 + int(self.circle_size * (n + 0.5)) + int(self.gap * n)
        y_pos = self.y1 + int(self.circle_size * 0.5)
        return (x_pos, y_pos)

    def _render(self):
        for num in self.range:
            pos = self._num_to_pos(num)
            blit(self.numbers[num], location=pos, registration=5)
        if self.response != None:
            pos = self._num_to_pos(self.response)
            blit(self.selected, location=pos, registration=5)

    def response_listener(self, queue):
        self._render()
        num = self.which_boundary(mouse_pos())
        if num != None:
            blit(self.mouseover, 5, self._num_to_pos(int(num)))
            for e in queue:
                if e.type == sdl2.SDL_MOUSEBUTTONDOWN:
                    self.response = int(num)
    
    @property
    def location(self):
        return self._location
        
    @location.setter
    def location(self, loc):
        self._location = loc
        self._init_bounds()
        
    @property
    def registration(self):
        return self._registration
        
    @registration.setter
    def registration(self, reg):
        self._registration = reg
        self._init_bounds()



class Slider(object):

    def __init__(self, width, diameter=60, fills={}, ticks=None, location=None):
        self.width = width
        self.ticks = ticks
        self.location = location if location else P.screen_c

        _fills = {'line': MED_GREY, 'slider': TRANSLUCENT_BLUE}
        _fills.update(fills) # override default colours if fills provided
        self.line = kld.Rectangle(width, 2, fill=_fills['line'])
        self.tick = kld.Rectangle(2, int(diameter/2), fill=_fills['line'])
        self.button = kld.Ellipse(diameter, fill=_fills['slider'])

        self.__clicked = False
        self.__dragging = False
        self.__drag_offset = 0
        self.__abs_pos = self.location

    def _draw_ticks(self):
        if self.ticks == 1:
            blit(self.tick, 5, self.location)
        elif self.ticks >= 2:
            blit(self.tick, 5, (self.xmin, self.location[1]))
            blit(self.tick, 5, (self.xmax, self.location[1]))
            if self.ticks > 2:
                spacing = float(self.width) / (self.ticks-1)
                for i in range(1, self.ticks-1):
                    blit(self.tick, 5, (self.xmin+int(spacing*i), self.location[1]))
        
    def draw(self):
        blit(self.line, 5, self.location)
        if self.ticks:
            self._draw_ticks()
        if self.__clicked:
            mp = mouse_pos()
            if self.__dragging:
                new_xpos = clip(mp[0]+self.__drag_offset, self.xmin, self.xmax)
                blit(self.button, 5, (new_xpos, self.location[1]))
            else:
                blit(self.button, 5, self.__abs_pos)
        
    def listen(self, queue):
        for e in queue:
            if e.type == sdl2.SDL_MOUSEBUTTONDOWN:
                click_pos = (e.button.x, e.button.y)
                if abs(click_pos[1]-self.location[1]) < self.button.diameter/2:
                    if self.xmin <= click_pos[0] <= self.xmax:
                        self.__abs_pos = (click_pos[0], self.location[1])
                        self.__clicked = True
                        self.__dragging = True
                        self.__drag_offset = 0
                    elif lsl(click_pos, self.__abs_pos) < self.button.diameter/2:
                       self.__clicked = True
                       self.__dragging = True
                       self.__drag_offset = self.__abs_pos[0] - click_pos[0]

            elif e.type == sdl2.SDL_MOUSEBUTTONUP:
                if self.__dragging:
                    release_pos = (e.button.x, e.button.y)
                    new_xpos = clip(release_pos[0]+self.__drag_offset, self.xmin, self.xmax)
                    self.__abs_pos = (new_xpos, self.location[1])
                    self.__dragging = False
        return False

    def reset(self):
        self.__clicked = False
                
    @property
    def location(self):
        return self.__location
        
    @location.setter
    def location(self, loc):
        self.__location = loc
        self.xmin = loc[0] - self.width//2
        self.xmax = loc[0] + self.width//2

    @property
    def pos(self):
        if self.__clicked == False:
            return None
        return (self.__abs_pos[0] - self.xmin) / (self.xmax - self.xmin)
        
    @pos.setter
    def pos(self, loc):
        if not (0.0 <= loc <= 1.0):
            raise ValueError("Slider position must be a float between 0 and 1, inclusive.")
        self.__abs_pos = (int(loc * self.width) + self.xmin, self.location[1])
        self.__clicked = True



class ThoughtProbe(BoundaryInspector):

    def __init__(self, choices, question, width, origin, order=None):

        BoundaryInspector.__init__(self)

        self.q = question
        self.width = width
        self.origin = origin

        if order == None:
            order = list(choices.keys())
            random.shuffle(order)
        self.order = order

        self.q_pad = 0.8 * message("ABCDEFG", "normal", blit_txt=False).height
        x1 = origin[0] - width//2
        x2 = origin[0] + width//2     
        y1 = origin[1] + self.q.height + self.q_pad * 2
       
        self.answers = {}
        for a in order:
            txt = message(choices[a], "normal", blit_txt=False, wrap_width=(width-self.q_pad//2), align='center')
            y2 = y1 + txt.height + self.q_pad
            bounds = RectangleBoundary(a, (x1, y1), (x2, y2))
            self.add_boundary(bounds)
            self.answers[a] = {'text': txt, 'location': (origin[0], y1), 'height': y2-y1}
            y1 = y2


    def _render(self):

        blit(self.q, location=self.origin, registration=8)
        for ans in self.order:
            a = self.answers[ans]
            ax, ay = a['location']
            blit(a['text'], location=(ax, ay + int(self.q_pad*0.55)), registration=8)

        mouseover = self.which_boundary(mouse_pos())
        if mouseover != None:
            a = self.answers[mouseover]
            hover = kld.Rectangle(self.width, a['height'], fill=TRANSLUCENT_GREY).render()
            blit(hover, 8, a['location'])


    def _collect(self):

        q = pump(True)
        ui_request(queue=q)
        for e in q:
            if e.type == sdl2.SDL_MOUSEBUTTONDOWN:
                coords = (e.button.x, e.button.y)
                response = self.which_boundary(coords)
                if response != None:
                    return response
        return None


    def collect(self):

        show_mouse_cursor()
        response = None
        onset = time.time()

        while response == None:
            fill()
            self._render()
            flip()
            response = self._collect()

        rt = time.time() - onset
        hide_mouse_cursor()
        return Response(response, rt)