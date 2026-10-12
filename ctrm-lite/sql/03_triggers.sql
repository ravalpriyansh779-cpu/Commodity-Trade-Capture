-- Keep updated_at current
CREATE OR REPLACE FUNCTION fn_touch_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trades_touch
BEFORE UPDATE ON trades
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

-- Audit every trade INSERT / UPDATE / DELETE.
-- Actor comes from the transaction-local setting app.current_user (set by the API).
CREATE OR REPLACE FUNCTION fn_audit_trades() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_user    TEXT := COALESCE(NULLIF(current_setting('app.current_user', true), ''), session_user::TEXT);
    v_changed JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.trade_id, 'INSERT', to_jsonb(NEW), v_user);
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        SELECT jsonb_object_agg(n.key, jsonb_build_object('old', to_jsonb(OLD) -> n.key, 'new', n.value))
        INTO v_changed
        FROM jsonb_each(to_jsonb(NEW)) n
        WHERE n.key <> 'updated_at' AND (to_jsonb(OLD) -> n.key) IS DISTINCT FROM n.value;

        IF v_changed IS NOT NULL THEN
            INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, changed_fields, changed_by)
            VALUES (TG_TABLE_NAME, NEW.trade_id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), v_changed, v_user);
        END IF;
        RETURN NEW;

    ELSE
        INSERT INTO audit_log (table_name, record_id, action, old_data, changed_by)
        VALUES (TG_TABLE_NAME, OLD.trade_id, 'DELETE', to_jsonb(OLD), v_user);
        RETURN OLD;
    END IF;
END;
$$;

CREATE TRIGGER trg_trades_audit
AFTER INSERT OR UPDATE OR DELETE ON trades
FOR EACH ROW EXECUTE FUNCTION fn_audit_trades();

-- Audit log is append-only
CREATE OR REPLACE FUNCTION fn_audit_immutable() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$;

CREATE TRIGGER trg_audit_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION fn_audit_immutable();
