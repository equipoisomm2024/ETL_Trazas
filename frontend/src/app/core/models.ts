// Interfaces TypeScript que reflejan los schemas Pydantic de la API

export type TipoDato = 'varchar' | 'text' | 'integer' | 'float' | 'datetime' | 'date' | 'boolean';
export const TIPOS_DATO: TipoDato[] = ['varchar', 'text', 'integer', 'float', 'datetime', 'date', 'boolean'];

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

export interface PatronExtraccion {
  id: number;
  id_parser: number;
  expresion_regular: string;
  orden: number;
  activo: boolean;
}

export interface CampoExtraccion {
  id: number;
  id_parser: number;
  nombre_grupo: string;
  campo_bd: string;
  tipo_dato: TipoDato;
  longitud: number | null;
  opcional: boolean;
  valor_defecto: string | null;
  orden: number;
}

export interface FuenteFichero {
  id: number;
  id_parser: number;
  ruta_patron: string;
  descripcion: string | null;
  activo: boolean;
}

export interface ConfiguracionParser {
  id: number;
  nombre: string;
  descripcion: string | null;
  tabla_destino: string;
  activo: boolean;
  fecha_creacion: string;
  fecha_modificacion: string;
  patrones: PatronExtraccion[];
  campos: CampoExtraccion[];
  fuentes: FuenteFichero[];
}

export interface ConfiguracionParserResumen {
  id: number;
  nombre: string;
  descripcion: string | null;
  tabla_destino: string;
  activo: boolean;
  fecha_creacion: string;
  fecha_modificacion: string;
  num_patrones: number;
  num_campos: number;
  num_fuentes: number;
}

export interface ConfiguracionParserCrear {
  nombre: string;
  descripcion?: string | null;
  tabla_destino: string;
  activo: boolean;
  patrones: Omit<PatronExtraccion, 'id' | 'id_parser'>[];
  campos: Omit<CampoExtraccion, 'id' | 'id_parser'>[];
  fuentes: Omit<FuenteFichero, 'id' | 'id_parser'>[];
}

// ---------------------------------------------------------------------------
// Ejecuciones
// ---------------------------------------------------------------------------

export interface ControlCarga {
  id: number;
  id_ejecucion: string;
  ruta_fichero: string;
  fecha_inicio: string;
  fecha_fin: string | null;
  estado: 'EN_PROCESO' | 'COMPLETADO' | 'ERROR';
  ultima_linea: number;
  lineas_procesadas: number;
  registros_insertados: number;
  mensaje_error: string | null;
}

export interface ListaEjecuciones {
  total: number;
  limit: number;
  offset: number;
  items: ControlCarga[];
}

export interface ProcesarRequest {
  fichero?: string | null;
  directorio?: string | null;
  usar_fuentes_bd?: boolean;
  forzar_completo?: boolean;
}

export interface ResultadoFichero {
  fichero: string;
  ok: boolean;
  parser?: string | null;
  id_ejecucion?: string | null;
  insertados?: number | null;
  lineas_procesadas?: number | null;
  error?: string | null;
}

export interface ProcesarResponse {
  total_ficheros: number;
  total_insertados: number;
  total_errores: number;
  resultados: ResultadoFichero[];
}
