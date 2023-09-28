__author__ = "Austin Hurst"

from klibs import STROKE_INNER
from klibs import P
from klibs.KLBoundary import BoundaryInspector, RectangleBoundary, CircleBoundary
from klibs.KLGraphics import fill, blit, flip, clear, rgb_to_rgba
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics.KLNumpySurface import NumpySurface as NpS
from klibs.KLCommunication import message
from klibs.KLEventQueue import flush, pump
from klibs.KLUserInterface import ui_request, key_pressed, get_clicks, mouse_clicked
from klibs.KLUtilities import show_mouse_cursor, hide_mouse_cursor, mouse_pos, clip
from klibs.KLUtilities import line_segment_len as lsl
from klibs.KLResponseCollectors import Response

import random
import time
import sdl2

MED_GREY = (128, 128, 128, 255)
LIGHT_GREY = (192, 192, 192, 255)
TRANSLUCENT_GREY = (192, 192, 192, 64)
TRANSLUCENT_BLUE = (0, 0, 128, 128)


class Aesthetics(object):
    """The aesthetic attributes to use for drawing an interface item.

    Args:
        color (tuple, optional): The RGBA color to use for the lines of the UI
            element. If not specified, `P.default_color` will be used.
        fill (tuple, optional): The RGBA color to use for the fill of the UI element.
            If not specified, no fill color will be used.
        thickness (int, optional): The thickness (in pixels) for the lines of the UI
            element. The default varies based on the element the aesthetic is used with.
        hover (tuple, optional): The translucent RGBA color to use for hover elements
            in the UI element. Defaults to translucent light grey.
        fontstyle (str, optional): The font style to use for rendering text within the
            UI element. Defaults to the 'default' font style.
        
    """
    def __init__(self, color=None, fill=None, thickness=None, hover=None, fontstyle=None):
        # Handle colours and thicknesses
        self._color = rgb_to_rgba(color) if color else P.default_color
        self._fill = rgb_to_rgba(fill) if fill else None
        self._thickness = int(thickness) if thickness else None
        self._hover = rgb_to_rgba(color) if hover else TRANSLUCENT_GREY
        self._fontstyle = fontstyle if fontstyle else 'default'

    @property
    def color(self):
        return self._color

    @property
    def fill(self):
        return self._fill

    @property
    def thickness(self):
        return self._thickness

    @property
    def hover(self):
        return self._hover

    @property
    def fontstyle(self):
        return self._fontstyle



class Button(object):
    
    def __init__(self, msg, width, height=None, aes=None, registration=5, location=None):

        # Initialize UI aesthetics
        if not aes:
            aes = Aesthetics(thickness=0)
        if aes.thickness is None:
            aes._thickness = 0
        
        self.width = width
        self.height = height if height else width
        self.msg = msg

        self.button = None
        if aes.thickness or aes.fill:
            outline = [aes.thickness, aes.color, STROKE_INNER]
            self.button = kld.Rectangle(self.width, self.height, outline, fill=aes.fill)
        self.button = kld.Rectangle(self.width, self.height)
        self.hover = kld.Rectangle(self.width, self.height, fill=aes.hover)
        
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
        if self.button:
            blit(self.button, 5, self.midpoint)
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
    """A Likert-type rating scale for collecting numeric responses.

    Args:
        first (int): The lowest digit on the scale.
        last (int): The highest digit on the scale.
        width (int): The full width of the scale.
        height (int): The height of each circle on the scale.

    """
    def __init__(
        self, first, last, width, height, aes=None, registration=None, location=None
    ):

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

        # Initialize UI aesthetics
        if not aes:
            aes = Aesthetics(thickness=0)
        if aes.thickness is None:
            aes._thickness = 0

        numlist = []
        for num in self.range:
            num_txt = message("{0}".format(num), aes.fontstyle)
            numlist.append((num, num_txt))
        self.numbers = dict(numlist)

        self.circle = None
        if aes.thickness > 0:
            outline = [aes.thickness, aes.color, STROKE_INNER]
            self.circle = kld.Ellipse(self.circle_size-4, stroke=outline, fill=aes.fill)
        self.selected = kld.Ellipse(self.circle_size-4, fill=aes.hover)
        self.mouseover = self.selected

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
            if self.circle:
                blit(self.circle, location=pos, registration=5)
            blit(self.numbers[num], location=pos, registration=5)
        if self.response != None:
            pos = self._num_to_pos(self.response)
            blit(self.selected, location=pos, registration=5)

    def update(self, queue):
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

    def __init__(self, choices, question, origin, width=None, order=None):

        BoundaryInspector.__init__(self)

        self.q = question
        self.width = self.q.width if width == None else width
        self.origin = origin
        hover_col = TRANSLUCENT_GREY

        if order == None:
            order = list(choices.keys())
            random.shuffle(order)
        self.order = order

        self.q_pad = 0.8 * message("ABCDEFG", "default").height
        x1 = origin[0] - (self.width // 2)
        x2 = origin[0] + (self.width // 2)     
        y1 = origin[1] + self.q.height + self.q_pad * 2

        # Render all response options and their hover boxes
        self.answers = {}
        max_width = 0
        for a in self.order:
            txt = message(choices[a], "default")
            if txt.width > max_width:
                max_width = txt.width
            hover_height = txt.height + self.q_pad
            self.answers[a] = {
                'text': txt,
                'hover': kld.Rectangle(self.width, hover_height, fill=hover_col),
            }

        # Calculate the location and boundary for each response option
        for a in self.order:
            y2 = y1 + self.answers[a]['text'].height + self.q_pad
            self.add_boundary(RectangleBoundary(a, (x1, y1), (x2, y2)))
            text_loc = (origin[0] - max_width // 2, y1 + int(self.q_pad * 0.55))
            self.answers[a]['location'] = text_loc
            y1 = y2


    def _render(self):

        blit(self.q, location=self.origin, registration=8)
        for ans in self.order:
            a = self.answers[ans]
            blit(a['text'], location=a['location'], registration=7)

        mouseover = self.which_boundary(mouse_pos())
        if mouseover != None:
            a = self.answers[mouseover]
            hover_loc = self.boundaries[mouseover].p1
            blit(a['hover'], 7, hover_loc)


    def _collect(self):
        q = pump(True)
        clicks = get_clicks(released=True, queue=q)
        for click in clicks:
            response = self.which_boundary(click)
            if response != None:
                return response
        return None


    def collect(self):

        show_mouse_cursor()
        response = None
        onset = time.time()

        flush()
        while response == None:
            fill()
            self._render()
            flip()
            response = self._collect()

        rt = time.time() - onset
        hide_mouse_cursor()
        return Response(response, rt)


class RatingScale(ThoughtProbe):
    # Special case of ThoughtProbe where all responses correspond to numbers, so
    # we allow for keypress responses as well as click responses

    def _collect(self):
        q = pump(True)
        # Check for clicks on response options
        clicks = get_clicks(released=True, queue=q)
        for click in clicks:
            response = self.which_boundary(click)
            if response != None:
                return response
        # Check for keypress events corresponding to rating scale options
        for event in q:
            if event.type == sdl2.SDL_KEYDOWN:
                keyname = sdl2.SDL_GetKeyName(event.key.keysym.sym)
                response = keyname.decode("utf-8").replace("Keypad ", "")
                if response in self.order:
                    return response
        return None
