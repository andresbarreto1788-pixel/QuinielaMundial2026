-- =====================================================================
--  Lógica de puntuación + avance automático del bracket
-- =====================================================================

-- ---------------------------------------------------------------------
-- Puntuación (resultado hasta el minuto 120, prórroga incl., sin penales)
--   3 -> marcador exacto
--   1 -> falla el marcador pero acierta el signo (ganador o empate)
--   0 -> falla marcador y signo
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION calcular_puntos(
    p_pred_local INT, p_pred_visit INT,
    p_real_local INT, p_real_visit INT
) RETURNS INT
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    IF p_real_local IS NULL OR p_real_visit IS NULL
       OR p_pred_local IS NULL OR p_pred_visit IS NULL THEN
        RETURN 0;
    END IF;

    IF p_pred_local = p_real_local AND p_pred_visit = p_real_visit THEN
        RETURN 3;
    END IF;

    IF sign(p_pred_local - p_pred_visit) = sign(p_real_local - p_real_visit) THEN
        RETURN 1;
    END IF;

    RETURN 0;
END;
$$;

-- ---------------------------------------------------------------------
-- Avance automático: al finalizar un partido, el clasificado se coloca
-- en el hueco (L/V) del siguiente partido del bracket.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION avanzar_ganador() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.estado = 'finalizado'
       AND NEW.ganador_equipo_id IS NOT NULL
       AND NEW.next_partido_id   IS NOT NULL THEN
        IF NEW.next_slot = 'L' THEN
            UPDATE partidos SET equipo_local_id = NEW.ganador_equipo_id
            WHERE id = NEW.next_partido_id;
        ELSE
            UPDATE partidos SET equipo_visitante_id = NEW.ganador_equipo_id
            WHERE id = NEW.next_partido_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_avanzar_ganador ON partidos;
CREATE TRIGGER trg_avanzar_ganador
    AFTER INSERT OR UPDATE OF estado, ganador_equipo_id ON partidos
    FOR EACH ROW EXECUTE FUNCTION avanzar_ganador();
