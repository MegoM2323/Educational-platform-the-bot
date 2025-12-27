{{/*
Expand the name of the chart.
*/}}
{{- define "thebot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "thebot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "thebot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "thebot.labels" -}}
helm.sh/chart: {{ include "thebot.chart" . }}
{{ include "thebot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
environment: {{ .Values.global.environment }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "thebot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "thebot.serviceAccountName" -}}
{{- if .Values.rbac.serviceAccount.create }}
{{- default (include "thebot.fullname" .) .Values.rbac.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.rbac.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend service name
*/}}
{{- define "thebot.backend.name" -}}
{{ include "thebot.fullname" . }}-backend
{{- end }}

{{/*
Frontend service name
*/}}
{{- define "thebot.frontend.name" -}}
{{ include "thebot.fullname" . }}-frontend
{{- end }}

{{/*
Celery service name
*/}}
{{- define "thebot.celery.name" -}}
{{ include "thebot.fullname" . }}-celery
{{- end }}

{{/*
Celery Beat service name
*/}}
{{- define "thebot.celeryBeat.name" -}}
{{ include "thebot.fullname" . }}-celery-beat
{{- end }}

{{/*
PostgreSQL service name
*/}}
{{- define "thebot.postgresql.name" -}}
{{ include "thebot.fullname" . }}-postgres
{{- end }}

{{/*
Redis service name
*/}}
{{- define "thebot.redis.name" -}}
{{ include "thebot.fullname" . }}-redis
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "thebot.configMapName" -}}
{{ .Values.configMap.name | default (printf "%s-config" (include "thebot.fullname" .)) }}
{{- end }}

{{/*
Secret name
*/}}
{{- define "thebot.secretName" -}}
{{ .Values.secrets.name | default (printf "%s-secrets" (include "thebot.fullname" .)) }}
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "thebot.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "thebot.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Celery selector labels
*/}}
{{- define "thebot.celery.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: celery
{{- end }}

{{/*
Celery Beat selector labels
*/}}
{{- define "thebot.celeryBeat.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: celery-beat
{{- end }}

{{/*
PostgreSQL selector labels
*/}}
{{- define "thebot.postgresql.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: postgresql
{{- end }}

{{/*
Redis selector labels
*/}}
{{- define "thebot.redis.selectorLabels" -}}
app.kubernetes.io/name: {{ include "thebot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis
{{- end }}
