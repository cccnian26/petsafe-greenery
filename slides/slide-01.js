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
  map?.startSlide({ slideNumber: 1, slideId: 'cover', title: 'PetSafe-Greenery' });

  slide.background = { color: theme.primary };

  const leaves = [
    { id: 'cover.leaf.01', x: 6.85, y: 0.35, w: 1.5, h: 2.1, rot: 315, c: theme.secondary },
    { id: 'cover.leaf.02', x: 8.15, y: 0.75, w: 0.85, h: 1.25, rot: 315, c: GOLD },
    { id: 'cover.leaf.03', x: 7.55, y: 2.85, w: 0.62, h: 0.95, rot: 315, c: SAND },
    { id: 'cover.leaf.04', x: 8.45, y: 3.25, w: 0.5, h: 0.78, rot: 315, c: '5FA894' },
    { id: 'cover.leaf.05', x: 6.45, y: 2.2, w: 0.44, h: 0.68, rot: 315, c: '2A9D8F' },
    { id: 'cover.leaf.06', x: 8.85, y: 2.1, w: 0.38, h: 0.6, rot: 315, c: 'E9C46A' },
  ];
  leaves.forEach((l) => {
    addMappedShape(slide, map, pres.shapes.TEAR, {
      elementId: l.id, role: 'decorative',
      x: l.x, y: l.y, w: l.w, h: l.h, rotate: l.rot,
      options: { fill: { color: l.c }, line: { color: l.c, width: 0 } },
      source: { file: 'slides/slide-01.js', method: 'addShape' },
    });
  });

  addMappedText(slide, map, {
    elementId: 'cover.title', role: 'title', text: 'PetSafe-Greenery',
    x: 0.7, y: 1.35, w: 6.2, h: 0.95,
    options: { fontSize: 46, bold: true, color: 'FFFFFF', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-01.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'cover.subtitle', role: 'subtitle',
    text: 'A Dual-Constraint Agentic Workflow for Pet-Friendly Balcony and Courtyard Planting Design',
    x: 0.7, y: 2.42, w: 6.0, h: 1.0,
    options: { fontSize: 17, color: 'E8EEEA', align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-01.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'cover.author', role: 'body',
    text: 'CHEN Niannian  |  26063619G\nCOMP5511: Artificial Intelligence Concepts\nThe Hong Kong Polytechnic University',
    x: 0.7, y: 3.75, w: 5.6, h: 1.1,
    options: { fontSize: 13, color: 'BFD2C8', align: 'left', valign: 'top', margin: 0, lineSpacingMultiple: 1.25, fontFace: 'Arial' },
    source: { file: 'slides/slide-01.js', method: 'addText' },
  });
  addMappedText(slide, map, {
    elementId: 'cover.date', role: 'body', text: 'Final presentation  |  20 or 27 November 2026',
    x: 0.7, y: 4.85, w: 5.6, h: 0.35,
    options: { fontSize: 11, color: GOLD, align: 'left', valign: 'top', margin: 0, fontFace: 'Arial' },
    source: { file: 'slides/slide-01.js', method: 'addText' },
  });
  slide.addNotes(NOTES['01']);
}

module.exports = { createSlide };
