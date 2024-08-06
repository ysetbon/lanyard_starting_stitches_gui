from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont, QFontMetrics, QImage
import logging
from attach_mode import AttachMode
from move_mode import MoveMode
from strand import Strand, AttachedStrand, MaskedStrand

class StrandDrawingCanvas(QWidget):
    def __init__(self, parent=None):
        """Initialize the StrandDrawingCanvas."""
        super().__init__(parent)
        self.setMinimumSize(700, 700)  # Set minimum size for the canvas
        self.initialize_properties()
        self.setup_modes()

    def initialize_properties(self):
        """Initialize all properties used in the StrandDrawingCanvas."""
        self.strands = []  # List to store all strands
        self.current_strand = None  # Currently active strand
        self.strand_width = 55  # Width of strands
        self.strand_color = QColor('purple')  # Default color for strands
        self.stroke_color = Qt.black  # Color for strand outlines
        self.stroke_width = 5  # Width of strand outlines
        self.highlight_color = Qt.red  # Color for highlighting selected strands
        self.highlight_width = 20  # Width of highlight
        self.is_first_strand = True  # Flag to indicate if it's the first strand being drawn
        self.selection_color = QColor(255, 0, 0, 128)  # Color for selection rectangle
        self.selected_strand_index = None  # Index of the currently selected strand
        self.layer_panel = None  # Reference to the layer panel
        self.selected_strand = None  # Currently selected strand
        self.last_selected_strand_index = None  # Index of the last selected strand
        self.strand_colors = {}  # Dictionary to store colors for each strand set
        self.grid_size = 30  # Size of grid cells
        self.show_grid = True  # Flag to show/hide grid
        self.should_draw_names = False  # Flag to show/hide strand names

    def setup_modes(self):
        """Set up attach and move modes."""
        self.attach_mode = AttachMode(self)
        self.attach_mode.strand_created.connect(self.on_strand_created)
        self.move_mode = MoveMode(self)
        self.current_mode = self.attach_mode  # Set initial mode to attach

    def paintEvent(self, event):
        """Handle paint events to draw the canvas contents."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.show_grid:
            self.draw_grid(painter)

        for strand in self.strands:
            if strand == self.selected_strand:
                self.draw_highlighted_strand(painter, strand)
            else:
                strand.draw(painter)

            if self.should_draw_names:
                self.draw_strand_label(painter, strand)

        if self.current_strand:
            self.current_strand.draw(painter)

        if isinstance(self.current_mode, MoveMode) and self.current_mode.selected_rectangle:
            painter.setBrush(QBrush(self.selection_color))
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRect(self.current_mode.selected_rectangle)

    def draw_grid(self, painter):
        """Draw the grid on the canvas."""
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for x in range(0, self.width(), self.grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self.grid_size):
            painter.drawLine(0, y, self.width(), y)

    def draw_strand_label(self, painter, strand):
        """Draw the label for a strand."""
        text = getattr(strand, 'layer_name', f"{strand.set_number}_1")
        mid_point = (strand.start + strand.end) / 2
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)

        metrics = painter.fontMetrics()
        text_width = metrics.width(text)
        text_height = metrics.height()

        text_rect = QRectF(mid_point.x() - text_width / 2, mid_point.y() - text_height / 2, text_width, text_height)

        text_path = QPainterPath()
        text_path.addText(text_rect.center().x() - text_width / 2, text_rect.center().y() + text_height / 4, font, text)

        painter.setPen(QPen(Qt.white, 6, Qt.SolidLine))
        painter.drawPath(text_path)

        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.fillPath(text_path, QBrush(Qt.black))
        painter.drawPath(text_path)

    def draw_highlighted_strand(self, painter, strand):
        """Draw a highlighted version of a strand."""
        if isinstance(strand, MaskedStrand):
            self.draw_highlighted_masked_strand(painter, strand)
        else:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            def set_highlight_pen(width_adjustment=0):
                pen = QPen(self.highlight_color, self.highlight_width + width_adjustment)
                pen.setJoinStyle(Qt.MiterJoin)
                pen.setCapStyle(Qt.SquareCap)
                painter.setPen(pen)

            set_highlight_pen()
            painter.drawPath(strand.get_path())

            set_highlight_pen(0.5)
            for i, has_circle in enumerate(strand.has_circles):
                if has_circle:
                    center = strand.start if i == 0 else strand.end
                    painter.drawEllipse(center, strand.width / 2, strand.width / 2)

            painter.restore()
            strand.draw(painter)

    def draw_highlighted_masked_strand(self, painter, masked_strand):
        """Draw a highlighted version of a masked strand."""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        temp_image = QImage(painter.device().size(), QImage.Format_ARGB32_Premultiplied)
        temp_image.fill(Qt.transparent)
        temp_painter = QPainter(temp_image)
        temp_painter.setRenderHint(QPainter.Antialiasing)

        masked_strand.draw(temp_painter)

        highlight_pen = QPen(self.highlight_color, self.stroke_width+4)
        highlight_pen.setJoinStyle(Qt.MiterJoin)
        highlight_pen.setCapStyle(Qt.SquareCap)
        temp_painter.setPen(highlight_pen)
        temp_painter.drawPath(masked_strand.get_mask_path())

        temp_painter.end()

        painter.drawImage(0, 0, temp_image)

        painter.restore()

    def set_layer_panel(self, layer_panel):
        """Set the layer panel and connect signals."""
        self.layer_panel = layer_panel
        self.layer_panel.draw_names_requested.connect(self.toggle_name_drawing)

    def toggle_name_drawing(self, should_draw):
        """Toggle the drawing of strand names."""
        self.should_draw_names = should_draw
        self.update()

    def enable_name_drawing(self):
        """Enable the drawing of strand names."""
        self.should_draw_names = True
        self.update()

    def deselect_all_strands(self):
        """Deselect all strands."""
        self.selected_strand = None
        self.selected_strand_index = None
        self.update()

    def update_color_for_set(self, set_number, color):
        """Update the color for a set of strands."""
        self.strand_colors[set_number] = color
        for strand in self.strands:
            if isinstance(strand, MaskedStrand):
                if strand.set_number.startswith(f"{set_number}_"):
                    strand.set_color(color)
                    self.update_attached_strands_color(strand, color)
            elif isinstance(strand, Strand) and strand.set_number == set_number:
                strand.set_color(color)
                self.update_attached_strands_color(strand, color)
        self.update()

    def update_attached_strands_color(self, parent_strand, color):
        """Recursively update the color of attached strands."""
        for attached_strand in parent_strand.attached_strands:
            attached_strand.set_color(color)
            self.update_attached_strands_color(attached_strand, color)

    def on_strand_created(self, strand):
        """Handle the creation of a new strand."""
        logging.info(f"Starting on_strand_created for strand: {strand.layer_name}")
        
        if hasattr(strand, 'is_being_deleted') and strand.is_being_deleted:
            logging.info("Strand is being deleted, skipping button creation")
            return

        if isinstance(strand, AttachedStrand):
            set_number = strand.parent.set_number
        elif self.selected_strand:
            set_number = self.selected_strand.set_number
        else:
            set_number = max(self.strand_colors.keys(), default=0) + 1

        strand.set_number = set_number

        if set_number not in self.strand_colors:
            self.strand_colors[set_number] = QColor('purple')
        strand.set_color(self.strand_colors[set_number])

        self.strands.append(strand)

        if self.layer_panel:
            set_number = int(strand.set_number) if isinstance(strand.set_number, str) else strand.set_number
            count = len([s for s in self.strands if s.set_number == set_number])
            strand.layer_name = f"{set_number}_{count}"
            
            # Only add a new button if it's a genuinely new strand, not during deletion
            if not hasattr(strand, 'is_being_deleted'):
                logging.info(f"Adding new layer button for set {set_number}, count {count}")
                self.layer_panel.add_layer_button(set_number, count)
            else:
                logging.info(f"Updating layer names for set {set_number}")
                self.layer_panel.update_layer_names(set_number)
            
            self.layer_panel.on_color_changed(set_number, self.strand_colors[set_number])

        if not isinstance(strand, AttachedStrand):
            self.select_strand(len(self.strands) - 1)
        
        self.update()
        
        # Notify LayerPanel that a new strand was added
        if self.layer_panel:
            self.layer_panel.update_attachable_states()
        
        logging.info("Finished on_strand_created")
    def attach_strand(self, parent_strand, new_strand):
        """Attach a new strand to a parent strand."""
        parent_strand.attached_strands.append(new_strand)
        new_strand.parent = parent_strand
        
        # Set the set_number for the new strand
        new_strand.set_number = parent_strand.set_number
        
        # Append the new strand to the strands list
        self.strands.append(new_strand)
        
        # Calculate the correct count for the new strand
        count = len([s for s in self.strands if s.set_number == new_strand.set_number])
        new_strand.layer_name = f"{new_strand.set_number}_{count}"
        
        # Set the color for the new strand
        if new_strand.set_number in self.strand_colors:
            new_strand.set_color(self.strand_colors[new_strand.set_number])
        
        # Update the layer panel
        if self.layer_panel:
            if not hasattr(new_strand, 'is_being_deleted'):
                self.layer_panel.add_layer_button(new_strand.set_number, count)
            else:
                self.layer_panel.update_layer_names(new_strand.set_number)
            self.layer_panel.on_strand_attached()
        
        # Update the canvas
        self.update()

    def add_strand(self, strand):
        """Add a strand to the canvas."""
        self.strands.append(strand)
        self.update()

    def select_strand(self, index):
        """Select a strand by index."""
        if 0 <= index < len(self.strands):
            self.selected_strand = self.strands[index]
            self.selected_strand_index = index
            self.last_selected_strand_index = index
            self.is_first_strand = False
            if self.layer_panel and self.layer_panel.get_selected_layer() != index:
                self.layer_panel.select_layer(index, emit_signal=False)
            self.current_mode = self.attach_mode
            self.current_mode.is_attaching = False
            self.current_strand = None
            self.update()
        else:
            self.selected_strand = None
            self.selected_strand_index = None

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        self.current_mode.mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        self.current_mode.mouseMoveEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        self.current_mode.mouseReleaseEvent(event)
        self.update()

    def set_mode(self, mode):
        """Set the current mode (attach or move)."""
        if mode == "attach":
            self.current_mode = self.attach_mode
            self.setCursor(Qt.ArrowCursor)
        elif mode == "move":
            self.current_mode = self.move_mode
            self.setCursor(Qt.OpenHandCursor)
        self.update()

    def remove_strand(self, strand):
        logging.info(f"Starting remove_strand for: {strand.layer_name}")
        if strand not in self.strands:
            logging.warning(f"Strand {strand.layer_name} not found in self.strands")
            return

        set_number, strand_number = map(int, strand.layer_name.split('_')[:2])
        is_main_strand = strand_number == 1

        # Collect all strands to be removed
        strands_to_remove = []
        masks_to_remove = []

        for s in self.strands:
            if is_main_strand:
                # Remove all strands in the same set and related masks
                if self.is_related_strand(s, set_number):
                    strands_to_remove.append(s)
                elif isinstance(s, MaskedStrand) and (
                    self.is_related_strand(s.first_selected_strand, set_number) or
                    self.is_related_strand(s.second_selected_strand, set_number)
                ):
                    masks_to_remove.append(s)
            else:
                # Remove only this specific strand and its masks
                if s == strand:
                    strands_to_remove.append(s)
                elif isinstance(s, MaskedStrand) and (
                    s.first_selected_strand == strand or s.second_selected_strand == strand
                ):
                    masks_to_remove.append(s)

        # Remove collected strands and masks
        for s in strands_to_remove + masks_to_remove:
            if s in self.strands:
                self.strands.remove(s)
                logging.info(f"Removed strand: {s.layer_name}")

                # Update selection if the removed strand was selected
                if self.selected_strand == s:
                    self.selected_strand = None
                    self.selected_strand_index = None
                    logging.info("Cleared selected strand")

        # Update parent strand's attached_strands list and circle if the removed strand is an AttachedStrand
        if isinstance(strand, AttachedStrand):
            parent = self.find_parent_strand(strand)
            if parent:
                # Remove the strand from the parent's attached_strands list
                parent.attached_strands.remove(strand)
                logging.info(f"Removed {strand.layer_name} from parent {parent.layer_name}'s attached strands")
                
                # Remove the circle from the parent strand
                if strand.start == parent.start:
                    parent.has_circles[0] = False
                elif strand.start == parent.end:
                    parent.has_circles[1] = False
                logging.info(f"Removed circle from parent {parent.layer_name}")

        # Update layer names only for the affected set if it's not a main strand
        if not is_main_strand:
            self.update_layer_names_for_set(set_number)
        else:
            self.update_set_numbers(set_number)

        # Refresh the layer panel
        if self.layer_panel:
            logging.info("Refreshing layer panel")
            self.layer_panel.refresh()

        self.update()
        logging.info("Finished remove_strand")

    def update_layer_names_for_set(self, set_number):
        logging.info(f"Updating layer names for set {set_number}")
        count = 1
        for strand in self.strands:
            if strand.set_number == set_number:
                new_name = f"{set_number}_{count}"
                if strand.layer_name != new_name:
                    logging.info(f"Updated strand name from {strand.layer_name} to {new_name}")
                    strand.layer_name = new_name
                count += 1
        if self.layer_panel:
            self.layer_panel.update_layer_names(set_number)
    def update_set_numbers(self, deleted_set_number):
            logging.info(f"Updating set numbers after deleting set {deleted_set_number}")
            for strand in self.strands:
                if strand.set_number > deleted_set_number:
                    strand.set_number -= 1
                    logging.info(f"Updated strand {strand.layer_name}'s set number to {strand.set_number}")
            
            # Update the strand_colors dictionary
            self.strand_colors = {k - 1 if k > deleted_set_number else k: v for k, v in self.strand_colors.items()}
            logging.info(f"Updated strand_colors: {self.strand_colors}")
            
            # Update the layer panel if it exists
            if self.layer_panel:
                logging.info("Updating LayerPanel set numbers")
                self.layer_panel.refresh()
            
            # Update layer names for all strands
            self.update_layer_names()
            logging.info("Finished update_set_numbers")
    def update_layer_names(self):
        logging.info("Starting update_layer_names")
        set_counts = {}
        affected_set_number = None
        for strand in self.strands:
            set_number = strand.set_number
            if set_number not in set_counts:
                set_counts[set_number] = 0
            set_counts[set_number] += 1
            new_name = f"{set_number}_{set_counts[set_number]}"
            if new_name != strand.layer_name:
                affected_set_number = set_number
                strand.layer_name = new_name
            logging.info(f"Updated layer name: {strand.layer_name}")
        
        # Update the layer panel if it exists, but only for the affected set
        if self.layer_panel and affected_set_number is not None:
            logging.info(f"Updating LayerPanel for affected set: {affected_set_number}")
            self.layer_panel.update_layer_names(affected_set_number)
        logging.info("Finished update_layer_names")
    def is_related_strand(self, strand, set_number):
        layer_name = strand.layer_name
        parts = layer_name.split('_')
        
        # Direct relationship: starts with set_number_
        if parts[0] == str(set_number):
            return True
        
        # Check for masked layers involving the set_number
        if len(parts) > 2 and str(set_number) in parts:
            return True
        
        return False

    def remove_attached_strands(self, parent_strand):
        """Recursively remove all attached strands."""
        attached_strands = parent_strand.attached_strands.copy()  # Create a copy to iterate over
        for attached_strand in attached_strands:
            if attached_strand in self.strands:
                self.strands.remove(attached_strand)
                self.remove_attached_strands(attached_strand)
        parent_strand.attached_strands.clear()  # Clear the list of attached strands

    def find_parent_strand(self, attached_strand):
        """Find the parent strand of an attached strand."""
        for strand in self.strands:
            if attached_strand in strand.attached_strands:
                return strand
        return None

    def clear_strands(self):
        """Clear all strands from the canvas."""
        self.strands.clear()
        self.current_strand = None
        self.is_first_strand = True
        self.selected_strand_index = None
        self.update()

    def snap_to_grid(self, point):
        """Snap a point to the nearest grid intersection."""
        return QPointF(
            round(point.x() / self.grid_size) * self.grid_size,
            round(point.y() / self.grid_size) * self.grid_size
        )

    def toggle_grid(self):
        """Toggle the visibility of the grid."""
        self.show_grid = not self.show_grid
        self.update()

    def set_grid_size(self, size):
        """Set the size of the grid cells."""
        self.grid_size = size
        self.update()

    def get_strand_at_position(self, pos):
        """Get the strand at the given position."""
        for strand in reversed(self.strands):  # Check from top to bottom
            if strand.get_path().contains(pos):
                return strand
        return None

    def get_strand_index(self, strand):
        """Get the index of a given strand."""
        try:
            return self.strands.index(strand)
        except ValueError:
            return -1

    def move_strand_to_front(self, strand):
        """Move a strand to the front (top) of the drawing order."""
        if strand in self.strands:
            self.strands.remove(strand)
            self.strands.append(strand)
            self.update()

    def move_strand_to_back(self, strand):
        """Move a strand to the back (bottom) of the drawing order."""
        if strand in self.strands:
            self.strands.remove(strand)
            self.strands.insert(0, strand)
            self.update()

    def get_bounding_rect(self):
        """Get the bounding rectangle of all strands."""
        if not self.strands:
            return QRectF()

        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for strand in self.strands:
            rect = strand.get_path().boundingRect()
            min_x = min(min_x, rect.left())
            min_y = min(min_y, rect.top())
            max_x = max(max_x, rect.right())
            max_y = max(max_y, rect.bottom())

        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def zoom_to_fit(self):
        """Zoom and center the view to fit all strands."""
        rect = self.get_bounding_rect()
        if not rect.isNull():
            self.fitInView(rect, Qt.KeepAspectRatio)
            self.update()

    def export_to_image(self, file_path):
        """Export the current canvas to an image file."""
        image = QImage(self.size(), QImage.Format_ARGB32)
        image.fill(Qt.white)

        painter = QPainter(image)
        self.render(painter)
        painter.end()

        image.save(file_path)

    def import_from_data(self, data):
        """Import strands from serialized data."""
        self.clear_strands()
        for strand_data in data:
            strand = Strand.from_dict(strand_data)
            self.add_strand(strand)
        self.update()

    def export_to_data(self):
        """Export strands to serializable data."""
        return [strand.to_dict() for strand in self.strands]

    def undo_last_action(self):
        """Undo the last action performed on the canvas."""
        # This method would require implementing an action history system
        pass

    def redo_last_action(self):
        """Redo the last undone action on the canvas."""
        # This method would require implementing an action history system
        pass

    def set_strand_width(self, width):
        """Set the width for new strands."""
        self.strand_width = width

    def set_default_strand_color(self, color):
        """Set the default color for new strands."""
        self.strand_color = color

    def set_highlight_color(self, color):
        """Set the highlight color for selected strands."""
        self.highlight_color = color
        self.update()

    def toggle_snap_to_grid(self):
        """Toggle snap-to-grid functionality."""
        self.snap_to_grid_enabled = not self.snap_to_grid_enabled

    def get_strand_count(self):
        """Get the total number of strands on the canvas."""
        return len(self.strands)

    def get_selected_strand(self):
        """Get the currently selected strand."""
        return self.selected_strand

    def clear_selection(self):
        """Clear the current strand selection."""
        self.selected_strand = None
        self.selected_strand_index = None
        self.update()

    def refresh_canvas(self):
        """Refresh the entire canvas, updating all strands."""
        for strand in self.strands:
            strand.update_shape()
        self.update()

# End of StrandDrawingCanvas class