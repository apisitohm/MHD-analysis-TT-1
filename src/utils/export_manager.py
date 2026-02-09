# src/utils/export_manager.py
import os
import matplotlib.pyplot as plt
from PIL import Image as PILImage, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import pyqtgraph.exporters  # Required for high-res export

class ExportManager:
    """Handles exporting of widgets to Images or PDF."""
    
    @staticmethod
    def export(config, widgets_map, context):
        fmt = config.get('format', 'image').lower()
        path = config.get('path', '')
        items = config.get('items', [])
        
        if not os.path.exists(path):
            os.makedirs(path)
            
        print(f"[ExportManager] Exporting {len(items)} items to {path} as {fmt}")
        
        # 1. Capture Images
        captured_images = {} 
        
        for key in items:
            widget_entry = widgets_map.get(key)
            if widget_entry:
                if isinstance(widget_entry, tuple) or isinstance(widget_entry, list):
                    widget_grab, widget_meta = widget_entry
                else:
                    widget_grab, widget_meta = widget_entry, widget_entry
                    
                title, desc = ExportManager.get_metadata(key, context, widget_meta)
                
                filename = f"{key}_{context['shot']}"
                if key in ['spectrogram', 'wavelet']:
                    roi = ExportManager.get_roi_range(widget_meta)
                    if roi:
                        filename += f"_{int(roi[0])}_{int(roi[1])}" 
                
                img_path = os.path.join(path, f"{filename}.png")
                
                # FIXED: Use smart grabber that handles PlotWidgets better
                ExportManager.grab_plot(widget_grab, img_path, title, desc)
                captured_images[key] = (img_path, desc) 
                
            elif key in ['init_phase_table', 'amp_signal_table']:
                title, desc = ExportManager.get_metadata(key, context, None)
                img_path = os.path.join(path, f"{key}_{context['shot']}.png")
                data = context.get(key, {})
                ExportManager.generate_table_image(data, img_path, title)
                captured_images[key] = (img_path, desc)

        # 2. PDF Generation
        if 'pdf' in fmt:
             pdf_path = os.path.join(path, f"Report_Shot{context['shot']}_{context['mode']}.pdf")
             ExportManager.save_pdf(captured_images, pdf_path, context)
    
    @staticmethod
    def get_roi_range(widget):
        if hasattr(widget, 'time_roi'):
            r = widget.time_roi.getRegion()
            return r
        if hasattr(widget, 'current_t_start') and hasattr(widget, 'current_t_end'):
            return (widget.current_t_start, widget.current_t_end)
        return None

    @staticmethod
    def get_metadata(key, context, widget):
        shot = context.get('shot', 'N/A')
        # [Metadata logic remains identical to your original code...]
        # (For brevity, I am not repeating the full metadata logic here as it was fine. 
        #  Assume the exact same get_metadata method as you provided.)
        
        # ... Paste your get_metadata code here ...
        # If you need me to paste it fully, let me know, but the bug is not here.
        # Below is a simplified version of what you had:
        roi_str = ""
        freq_str = ""
        param_str = ""
        
        t_start, t_end = 0, 0
        f_center, f_width = 0, 0
        
        if widget:
            if hasattr(widget, 'time_roi'):
                 r = widget.time_roi.getRegion()
                 t_start, t_end = r[0], r[1]
                 roi_str = f"Time: {t_start:.2f}-{t_end:.2f} ms"
            elif hasattr(widget, 'current_t_start'):
                 t_start, t_end = widget.current_t_start, widget.current_t_end
                 roi_str = f"Time: {t_start:.2f}-{t_end:.2f} ms"
            if hasattr(widget, 'freq_line'):
                 f_center = widget.freq_line.value() / 1000.0
            elif hasattr(widget, 'current_freq'):
                 f_center = widget.current_freq / 1000.0
            if hasattr(widget, 'txt_f_width'):
                try: f_width = float(widget.txt_f_width.text())
                except: pass
            elif hasattr(widget, 'current_dfreq'):
                f_width = widget.current_dfreq / 1000.0
            if f_center > 0:
                freq_str = f"Freq: {f_center:.2f} +/- {f_width:.2f} kHz"
            if hasattr(widget, 'combo_overlay_param'):
                param_str = f"Param: {widget.combo_overlay_param.currentText()}"
        
        extra_info = [x for x in [roi_str, freq_str, param_str] if x]
        info_line = " | ".join(extra_info)
        
        title = f"{key.replace('_', ' ').title()} - Shot {shot}"
        desc = info_line
        
        # Specific overrides
        if key == 'spectrogram': title = f"Spectrogram - Shot {shot}"
        elif key == 'wavelet': 
            title = f"Wavelet - Shot {shot}"
            if hasattr(widget, 'guide_manager') and widget.guide_manager.current_guide:
                desc += " | Guide Active"
        elif key == 'phase_diff_coil':
            title = f"Phase Diff vs Coil Loc - Shot {shot}"
            if hasattr(widget, 'fit_plot'): desc += f" | {widget.fit_plot.plotItem.titleLabel.text}"
        elif key == 'phase_cycle':
             title = f"Phase Cycle - Shot {shot}"
             if hasattr(widget, 'cycle_plot'): desc += f" | {widget.cycle_plot.plotItem.titleLabel.text}"

        return title, desc

    @staticmethod
    def grab_plot(widget, save_path, title, description):
        """Captures Widget to image file. Uses ImageExporter if available for high-res."""
        
        # 1. Try High-Res Export (Fixes Cropped Images)
        success = False
        try:
            # Check for standard PyQtGraph PlotWidget or PlotItem
            target_item = None
            if hasattr(widget, 'plotItem'): # It's a PlotWidget
                target_item = widget.plotItem
            elif hasattr(widget, 'scene'): # It's a GraphicsLayoutWidget
                target_item = widget.scene()
            
            if target_item:
                # Export at fixed width (e.g., 1920px) to ensure quality and full axes
                exporter = pyqtgraph.exporters.ImageExporter(target_item)
                exporter.parameters()['width'] = 1920 
                exporter.export(save_path)
                success = True
        except Exception as e:
            print(f"High-res export failed, using fallback: {e}")

        # 2. Fallback to Screen Capture (grab)
        if not success:
            pixmap = widget.grab()
            pixmap.save(save_path)
        
        # 3. Add Title/Desc using PIL (Same as before)
        try:
            img = PILImage.open(save_path)
            header_h = 70
            new_img = PILImage.new('RGB', (img.width, img.height + header_h), 'white')
            new_img.paste(img, (0, header_h))
            
            draw = ImageDraw.Draw(new_img)
            try:
                font_title = ImageFont.truetype("arial.ttf", 28)
                font_desc = ImageFont.truetype("arial.ttf", 18)
            except:
                font_title = ImageFont.load_default()
                font_desc = ImageFont.load_default()
                
            draw.text((15, 10), title, font=font_title, fill='black')
            draw.text((15, 45), description, font=font_desc, fill='black')
            new_img.save(save_path)
        except Exception as e:
            print(f"Error adding title: {e}")

    @staticmethod
    def generate_table_image(data_dict, save_path, title):
        # [Same as your original code]
        if not data_dict: data_dict = {'-': 0}
        num_rows = len(data_dict) + 1
        fig, ax = plt.subplots(figsize=(6, max(4, num_rows * 0.5)))
        ax.axis('tight'); ax.axis('off')
        
        table_data = [["Channel", "Value"]]
        for k in sorted(data_dict.keys()):
            name = f"CH{k+1}" if isinstance(k, int) else str(k)
            table_data.append([name, f"{data_dict[k]:.2f}"])
            
        table = ax.table(cellText=table_data, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 1.5)
        plt.title(title)
        plt.savefig(save_path, bbox_inches='tight', dpi=150)
        plt.close()

    @staticmethod
    def save_pdf(image_paths_map, pdf_path, context):
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = styles['Title']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # --- Report Header ---
        elements.append(Paragraph(f"Analysis Report", title_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # --- Config Summary ---
        elements.append(Paragraph("Configuration Summary", heading_style))
        dur = context.get('duration', 0.0)
        ip = context.get('ip_max', 0.0)
        config_text = [
            f"<b>Shot No:</b> {context.get('shot', 'N/A')}",
            f"<b>Mode:</b> {context.get('mode', 'N/A')} / {context.get('type', 'N/A')}",
            f"<b>Duration:</b> {dur:.2f} ms",
            f"<b>IP Max:</b> {ip:.2f} kA",
        ]
        for line in config_text:
             elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # --- Sections ---
        pairs = [
            (['spectrogram', 'wavelet'], "Time-Frequency Analysis"),
            (['wavelet_peaks_phase_diff', 'phase_diff_coil'], "Phase Difference Analysis"),
            (['wavelet_peaks_phase_cycle', 'phase_cycle'], "Phase Cycle Analysis"),
            (['singular_values', 'spatial_structure'], "SVD & Spatial Structure"),
            (['init_phase_table', 'amp_signal_table'], "Parameter Configuration")
        ]
        
        active_sections = []
        for keys, section_title in pairs:
            display_keys = [k for k in keys if k in image_paths_map]
            if display_keys:
                active_sections.append((display_keys, section_title))
        
        for idx, (display_keys, section_title) in enumerate(active_sections):
            # FIXED: Add PageBreak BEFORE new section (except the first one)
            # This prevents trailing spacers from creating blank pages
            if idx > 0:
                elements.append(PageBreak())

            elements.append(Paragraph(section_title, heading_style))
            elements.append(Spacer(1, 0.1*inch))
            
            for i, key in enumerate(display_keys):
                data = image_paths_map[key]
                img_path, desc = data if isinstance(data, tuple) else (data, "")
                    
                try:
                    img = Image(img_path)
                    
                    # Aspect Ratio Logic
                    iw, ih = img.wrap(0,0) 
                    aspect = ih / float(iw)
                    display_width = 6*inch 
                    display_height = display_width * aspect
                    
                    # Height Cap
                    if display_height > 4.2*inch:
                         display_height = 4.2*inch
                         display_width = display_height / aspect
                        
                    img.drawHeight = display_height
                    img.drawWidth = display_width
                    
                    elements.append(img)
                    elements.append(Spacer(1, 0.05*inch))
                    
                    if desc:
                        elements.append(Paragraph(desc, normal_style))
                    
                    # FIXED: Only add spacer if it's NOT the last image in the section
                    if i < len(display_keys) - 1:
                        elements.append(Spacer(1, 0.15*inch))
                    
                except Exception as e:
                    print(f"Error embedding image {key}: {e}")
            
        try:
            doc.build(elements)
        except Exception as e:
            print(f"PDF Build Error: {e}")