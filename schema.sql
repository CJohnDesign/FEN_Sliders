-- Create Presentations table
CREATE TABLE Presentations (
    presentation_id VARCHAR(10) PRIMARY KEY,
    theme VARCHAR(255),
    title VARCHAR(255),
    info TEXT,
    vertical_center BOOLEAN,
    layout VARCHAR(50),
    theme_config JSON,
    transition VARCHAR(50),
    drawings JSON
);

-- Create Slides table
CREATE TABLE Slides (
    slide_id SERIAL PRIMARY KEY,
    presentation_id VARCHAR(10) REFERENCES Presentations(presentation_id) ON DELETE CASCADE,
    slide_number INT NOT NULL,
    header_content TEXT,
    body_content TEXT,
    layout VARCHAR(50),
    image VARCHAR(255),
    transition VARCHAR(50),
    arrows JSON
);

-- Insert example presentation
INSERT INTO Presentations (
    presentation_id, theme, title, info, vertical_center, layout, theme_config, transition, drawings
) VALUES (
    'FEN_MF1',
    '../../',
    'MedFirst 1 Plan Overview',
    'Slidev Deck for MedFirst 1 Plan Overview',
    TRUE,
    'intro',
    '{"logoHeader": "img/logo.svg", "audioEnabled": true}',
    'fade-out',
    '{"persist": false}'
);

-- Insert example slides
INSERT INTO Slides (
    presentation_id, slide_number, header_content, body_content, layout, image, transition, arrows
) VALUES
(
    'FEN_MF1', 1,
    '# MedFirst 1 Plan Overview',
    'Understand the details and benefits of the **MedFirst 1 Plan**.',
    'intro', NULL, 'fade-out', NULL
),
(
    'FEN_MF1', 2, NULL, NULL,
    'one-half-img-center',
    'img/mf1.jpg', 'fade-out',
    '[{"x1":350,"y1":10,"x2":410,"y2":80,"color":"var(--slidev-theme-accent)"},{"x1":150,"y1":413,"x2":310,"y2":413,"color":"var(--slidev-theme-accent)"}]'
),
(
    'FEN_MF1', 3,
    '## Primary Care Office Visit',
    '- Visit Allowance: 3 visits per year\n- Visit Co-Payment: $25\n- Annual Max: $150',
    'one-half-img',
    'img/mf1.jpg', 'fade-out',
    '[{"x1":410,"y1":410,"x2":540,"y2":410,"color":"var(--slidev-theme-accent)"}]'
); 