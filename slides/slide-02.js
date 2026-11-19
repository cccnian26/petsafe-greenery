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
  map?.startSlide({ slideNumber: 2, slideId: 'problem', title: 'The problem' });
  title(slide, map, 'problem.title', 'The problem', theme);

  addMappedText(slide, map, {
    elementId: 'problem.headline', role: 'heading',
    text: '"Beautiful for you. Fatal for your cat."',
    x: 0.55, y: 1.02, w: 8.9, h: 0.5,
    options: { fontSize: 21, bold: true, color: theme.accent, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-02.js', method: 'addText' },
  });

  const cards = [
    { id: 'problem.card.01', name: 'True Lily', latin: 'Lilium spp.', pet: 'Cats', effect: 'Acute renal failure' },
    { id: 'problem.card.02', name: 'Sago Palm', latin: 'Cycas revoluta', pet: 'Dogs', effect: 'Liver failure' },
    { id: 'problem.card.03', name: 'Pothos / Peace Lily', latin: 'Epipremnum aureum', pet: 'Both pets', effect: 'Calcium oxalate crystals' },
  ];
  cards.forEach((c, i) => {
    const x = 0.55 + i * 3.05;
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: c.id + '.card', role: 'card',
      x: x, y: 1.68, w: 2.8, h: 2.45,
      options: { fill: { color: 'F6F7F6' }, line: { color: 'D8DEDC', width: 1 }, rectRadius: 0.06 },
      source: { file: 'slides/slide-02.js', method: 'addShape' },
    });
    addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
      elementId: c.id + '.badge', role: 'decorative',
      x: x + 0.22, y: 1.9, w: 0.86, h: 0.34,
      options: { fill: { color: theme.accent }, line: { color: theme.accent, width: 0 }, rectRadius: 0.05 },
      source: { file: 'slides/slide-02.js', method: 'addShape' },
    });
    addMappedText(slide, map, {
      elementId: c.id + '.pet', role: 'label', text: c.pet,
      x: x + 0.22, y: 1.96, w: 0.86, h: 0.26,
      options: { fontSize: 9, bold: true, color: 'FFFFFF', align: 'center', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-02.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: c.id + '.name', role: 'heading', text: c.name,
      x: x + 0.22, y: 2.38, w: 2.4, h: 0.4,
      options: { fontSize: 16, bold: true, color: theme.primary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-02.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: c.id + '.latin', role: 'body', text: c.latin,
      x: x + 0.22, y: 2.76, w: 2.4, h: 0.28,
      options: { fontSize: 11, italic: true, color: theme.secondary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-02.js', method: 'addText' },
    });
    addMappedText(slide, map, {
      elementId: c.id + '.effect', role: 'body', text: c.effect,
      x: x + 0.22, y: 3.12, w: 2.4, h: 0.6,
      options: { fontSize: 12.5, color: theme.primary, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
      source: { file: 'slides/slide-02.js', method: 'addText' },
    });
  });

  addMappedShape(slide, map, pres.shapes.ROUNDED_RECTANGLE, {
    elementId: 'problem.callout', role: 'card',
    x: 0.55, y: 4.35, w: 8.9, h: 0.72,
    options: { fill: { color: theme.primary }, line: { color: theme.primary, width: 0 }, rectRadius: 0.05 },
    source: { file: 'slides/slide-02.js', method: 'addShape' },
  });
  addMappedText(slide, map, {
    elementId: 'problem.callout.text', role: 'body',
    text: '700+ ornamental species are dangerous to cats or dogs -- and LLMs recommend them, because toxicity is a fact the model cannot check for itself.',
    x: 0.8, y: 4.47, w: 8.4, h: 0.5,
    options: { fontSize: 13, color: 'FFFFFF', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-02.js', method: 'addText' },
  });
  pageNumber(slide, map, 2, theme);
  slide.addNotes(NOTES['02']);
}

module.exports = { createSlide };
