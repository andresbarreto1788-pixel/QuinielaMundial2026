-- =====================================================================
--  Seed Data v2 — Bracket completo Mundial 2026
--
--  * 32 equipos (16avos de final) -> Octavos -> Cuartos -> Semis -> Final
--  * El árbol se enlaza con una fórmula genérica (sin IDs a mano).
--  * Canadá 2-1 Sudáfrica YA jugado: el trigger avanza a Canadá y las
--    predicciones reproducen los puntos iniciales (3pts=6, 1pt=16, 0pt=4).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Equipos (bandera = emoji). Editar aquí si alguna no coincide.
-- ---------------------------------------------------------------------
-- 32 selecciones reales clasificadas a 16avos (Mundial 2026). Código = ISO alpha-2 (flagcdn).
INSERT INTO equipos (nombre, bandera, codigo) VALUES
    ('Alemania','🇩🇪','de'), ('Paraguay','🇵🇾','py'), ('Francia','🇫🇷','fr'), ('Suecia','🇸🇪','se'),
    ('Canadá','🇨🇦','ca'), ('Sudáfrica','🇿🇦','za'), ('Países Bajos','🇳🇱','nl'), ('Marruecos','🇲🇦','ma'),
    ('Portugal','🇵🇹','pt'), ('Croacia','🇭🇷','hr'), ('España','🇪🇸','es'), ('Austria','🇦🇹','at'),
    ('Estados Unidos','🇺🇸','us'), ('Bosnia','🇧🇦','ba'), ('Bélgica','🇧🇪','be'), ('Senegal','🇸🇳','sn'),
    ('Brasil','🇧🇷','br'), ('Japón','🇯🇵','jp'), ('Costa de Marfil','🇨🇮','ci'), ('Noruega','🇳🇴','no'),
    ('México','🇲🇽','mx'), ('Ecuador','🇪🇨','ec'), ('Inglaterra','🏴','gb-eng'), ('RD Congo','🇨🇩','cd'),
    ('Argentina','🇦🇷','ar'), ('Cabo Verde','🇨🇻','cv'), ('Australia','🇦🇺','au'), ('Egipto','🇪🇬','eg'),
    ('Suiza','🇨🇭','ch'), ('Argelia','🇩🇿','dz'), ('Colombia','🇨🇴','co'), ('Ghana','🇬🇭','gh');

-- ---------------------------------------------------------------------
-- 2) Partidos de 16avos (ronda 1). orden 1..16 (1-8 izquierda, 9-16 derecha)
-- ---------------------------------------------------------------------
-- Cruces, fechas y sedes oficiales (ordenados para que el árbol de Octavos coincida con FIFA)
INSERT INTO partidos (ronda, nombre_ronda, orden, equipo_local_id, equipo_visitante_id, fecha_texto, sede)
SELECT 1, '16avos de final', v.orden, el.id, ev.id, v.fecha, NULLIF(v.sede, '')
FROM (VALUES
    ( 1, 'Alemania',       'Paraguay',     'Lun 29 jun · 17:30', 'Gillette Stadium, Boston'),
    ( 2, 'Francia',        'Suecia',       'Mar 30 jun · 18:00', 'MetLife Stadium, Nueva Jersey'),
    ( 3, 'Canadá',         'Sudáfrica',    'Dom 28 jun · 16:00', 'SoFi Stadium, Los Ángeles'),
    ( 4, 'Países Bajos',   'Marruecos',    'Lun 29 jun · 22:00', 'Estadio BBVA, Monterrey'),
    ( 5, 'Portugal',       'Croacia',      'Jue 2 jul · 20:00',  ''),
    ( 6, 'España',         'Austria',      'Jue 2 jul · 16:00',  ''),
    ( 7, 'Estados Unidos', 'Bosnia',       'Mié 1 jul · 21:00',  ''),
    ( 8, 'Bélgica',        'Senegal',      'Mié 1 jul · 17:00',  ''),
    ( 9, 'Brasil',         'Japón',        'Lun 29 jun · 14:00', 'NRG Stadium, Houston'),
    (10, 'Costa de Marfil','Noruega',      'Mar 30 jun · 14:00', 'AT&T Stadium, Dallas'),
    (11, 'México',         'Ecuador',      'Mar 30 jun · 22:00', 'Estadio Azteca, Ciudad de México'),
    (12, 'Inglaterra',     'RD Congo',     'Mié 1 jul · 13:00',  ''),
    (13, 'Argentina',      'Cabo Verde',   'Vie 3 jul · 19:00',  'Hard Rock Stadium, Miami'),
    (14, 'Australia',      'Egipto',       'Vie 3 jul · 15:00',  ''),
    (15, 'Suiza',          'Argelia',      'Vie 3 jul · 00:00',  ''),
    (16, 'Colombia',       'Ghana',        'Vie 3 jul · 22:30',  '')
) AS v(orden, local, visita, fecha, sede)
JOIN equipos el ON el.nombre = v.local
JOIN equipos ev ON ev.nombre = v.visita;

-- Rondas siguientes (equipos por definir; se llenan con el trigger)
INSERT INTO partidos (ronda, nombre_ronda, orden)
SELECT 2, 'Octavos de final',  g FROM generate_series(1, 8) g;
INSERT INTO partidos (ronda, nombre_ronda, orden)
SELECT 3, 'Cuartos de final',  g FROM generate_series(1, 4) g;
INSERT INTO partidos (ronda, nombre_ronda, orden)
SELECT 4, 'Semifinal',         g FROM generate_series(1, 2) g;
INSERT INTO partidos (ronda, nombre_ronda, orden)
SELECT 5, 'Final',             1;

-- ---------------------------------------------------------------------
-- 3) Enlace del árbol: cada partido alimenta al de la ronda siguiente.
--    orden_siguiente = (orden+1)/2 ; hueco = L si orden impar, V si par.
-- ---------------------------------------------------------------------
UPDATE partidos p
SET next_partido_id = n.id,
    next_slot       = CASE WHEN p.orden % 2 = 1 THEN 'L' ELSE 'V' END
FROM partidos n
WHERE n.ronda = p.ronda + 1
  AND n.orden = (p.orden + 1) / 2
  AND p.ronda < 5;

-- ---------------------------------------------------------------------
-- 4) Usuarios
-- ---------------------------------------------------------------------
INSERT INTO usuarios (nombre) VALUES
    ('Catira'), ('Yaurys'), ('Carlexy'), ('Caren'), ('Uli'), ('Eva'),
    ('Betty'), ('Belmary'), ('Mario'), ('Maribel'), ('Yonnata'), ('Andrés'),
    ('Nathalia'), ('Carlos'), ('Fernando'), ('Carmen'), ('Chandy'), ('Coco'),
    ('Toro'), ('Mateo'), ('Gaby'), ('Sofía'),
    ('Gladys'), ('Luis'), ('Fernando Andrés'), ('Pedro');

-- ---------------------------------------------------------------------
-- 5) Resultado oficial ya jugado: Canadá 1 - 0 Sudáfrica.
--    El trigger coloca a Canadá en los Octavos automáticamente.
-- ---------------------------------------------------------------------
UPDATE partidos
SET goles_local       = 1,
    goles_visitante   = 0,
    ganador_equipo_id = (SELECT id FROM equipos WHERE nombre = 'Canadá'),
    estado            = 'finalizado'
WHERE id = (
    SELECT m.id FROM partidos m
    JOIN equipos el ON el.id = m.equipo_local_id
    JOIN equipos ev ON ev.id = m.equipo_visitante_id
    WHERE el.nombre = 'Canadá' AND ev.nombre = 'Sudáfrica'
);

-- ---------------------------------------------------------------------
-- 6) Predicciones del Canadá vs Sudáfrica (reproducen los puntos iniciales)
-- ---------------------------------------------------------------------
INSERT INTO predicciones (usuario_id, partido_id, goles_local, goles_visitante)
SELECT u.id, m.id, v.gl, v.gv
FROM (VALUES
    -- 3 PUNTOS: marcador exacto 1-0
    ('Catira',1,0), ('Yaurys',1,0), ('Carlexy',1,0),
    ('Caren',1,0),  ('Uli',1,0),    ('Eva',1,0),
    -- 1 PUNTO: gana Canadá pero con otro marcador (≠ 1-0)
    ('Betty',2,0), ('Belmary',3,1), ('Mario',2,0), ('Maribel',3,2),
    ('Yonnata',4,1), ('Andrés',2,0), ('Nathalia',3,0), ('Carlos',2,1),
    ('Fernando',4,2), ('Carmen',3,1), ('Chandy',2,0), ('Coco',5,1),
    ('Toro',2,0), ('Mateo',3,2), ('Gaby',4,0), ('Sofía',2,1),
    -- 0 PUNTOS: empate o gana Sudáfrica
    ('Gladys',1,1), ('Luis',0,1), ('Fernando Andrés',1,2), ('Pedro',0,0)
) AS v(nombre, gl, gv)
JOIN usuarios u ON u.nombre = v.nombre
CROSS JOIN (
    SELECT m.id FROM partidos m
    JOIN equipos el ON el.id = m.equipo_local_id
    JOIN equipos ev ON ev.id = m.equipo_visitante_id
    WHERE el.nombre = 'Canadá' AND ev.nombre = 'Sudáfrica'
) m;
