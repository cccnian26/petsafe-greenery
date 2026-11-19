const path = require('path');
const NOTES = require('./notes');
const { addMappedText, addMappedShape, addMappedImage } = require('/workspace/.plugin-cache/sha256-tree-v1-6562a7a9a9a69af61724f6f5a3cf2b2049410641553731506ce9071693edf57c/skills/pptx/scripts/mavis-ppt-map.cjs');

const FIG = path.join(__dirname, '..', 'figures');
const GOLD = 'E9C46A';
const SAND = 'F4A261';

function pageNumber(slide, map, n, theme) {
  addMappedText(slide, map, {
    elementId: 'page.number.' + n, role: 'pageNumber', text: String(n),
    x: 9.3, y: 5.08, w: 0.45, h: 0.3,
    options: { fontSize: 10, color: theme.secondary, align: 'right', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}

function title(slide, map, id, text, theme) {
  addMappedText(slide, map, {
    elementId: id, role: 'title', text: text,
    x: 0.55, y: 0.34, w: 8.9, h: 0.6,
    options: { fontSize: 27, bold: true, color: theme.primary, align: 'left',
               margin: 0, fontFace: 'Arial', fit: 'shrink' },
    source: { file: 'slides/slide-%s.js', method: 'addText' },
  });
}


function createSlide(pres, theme) {
  const slide = pres.addSlide();
  const map = pres.__mavisElementMap;
  map?.startSlide({ slideNumber: 10, slideId: 'conclusion', title: 'Conclusion' });
  slide.background = { color: theme.primary };

  addMappedText(slide, map, {
    elementId: 'conclusion.title', role: 'title', text: 'Every checkable constraint belongs in code.',
    x: 0.7, y: 0.95, w: 8.6, h: 0.8,
    options: { fontSize: 30, bold: true, color: 'FFFFFF', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial', fit: 'shrink' },
    source: { file: 'slides/slide-10.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'conclusion.subtitle', role: 'subtitle',
    text: 'The LLM designs; deterministic code decides what is allowed, and checks what came back.',
    x: 0.7, y: 1.78, w: 8.2, h: 0.42,
    options: { fontSize: 15, color: GOLD, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-10.js', method: 'addText' },
  });

  const chips = [
    '150-species ground truth',
    'reproducible data pipeline',
    '25-scenario benchmark',
    'deterministic completeness rubric',
    'live demo',
  ];
  chips.forEach((c, i) => {
    const x = 0.7 + (i % 3) * 3.0;
    const y = 2.45 + Math.floor(i / 3) * 0.72;
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: 'conclusion.chip.' + (i + 1) + '.shape', role: 'decorative',
      x: x, y: y, w: 2.8, h: 0.56,
      options: { fill: { color: '33505A' }, line: { color: '4A6B73', width: 1 }, rectRadius: 0.05 },
      source: { file: 'slides/slide-10.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: 'conclusion.chip.' + (i + 1) + '.text', role: 'body', text: c,
      x: x + 0.12, y: y + 0.15, w: 2.56, h: 0.28,
      options: { fontSize: 11, color: 'E4EDE8', align: 'center', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-10.js', method: 'addText' },
    });
  });

  addMappedText(slide, map, {
    elementId: 'conclusion.links', role: 'body',
    text: 'github.com/<your-id>/petsafe-greenery      |      <your-id>.streamlit.app',
    x: 0.7, y: 4.18, w: 8.6, h: 0.34,
    options: { fontSize: 12, color: '9FC7BA', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-10.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'conclusion.qa', role: 'heading', text: 'Questions?',
    x: 0.7, y: 4.62, w: 3.0, h: 0.45,
    options: { fontSize: 20, bold: true, color: GOLD, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-10.js', method: 'addText' },
  });
  pageNumber(slide, map, 10, theme);
  slide.addNotes(NOTES['10']);
}

module.exports = { createSlide };
