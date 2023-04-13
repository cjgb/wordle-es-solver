##############################################################################################
# @gilbellosta 2022-12-09
# Find the "optimal path" to a solution
##############################################################################################

library(plyr)
library(reshape2)

args <- commandArgs(trailingOnly = TRUE)

my_target <- args[1]
my_guess  <- args[2]

if (is.na(my_guess)) my_guess <- "seria"

my_corpus   <- readRDS("data/my_corpus.rds")
popularidad <- readRDS("data/popularidad.rds")

# -----------------------------------------------------------------------------
# Función para seleccionar solo las palabras que cumplen ciertos requisitos
# -----------------------------------------------------------------------------

filtra_corpus <- function(corpus, estado) {
  res <- corpus

  # only words matching known correct/green letters
  for (i in 1:5) {
    if (estado$p[i] != "")
      res <- res[res[, i] == estado$p[i], , drop = FALSE]

    if (!is.null(estado$n[[i]]))
      res <- res[!res[, i] %in% estado$n[[i]], , drop = FALSE]

    if (!is.null(estado$excluidas))
      res <- res[!res[, i] %in% estado$excluidas, , drop = FALSE]
  }

  # sanity check
  if (nrow(res) == 0)
    stop("No hay candidatos en el corpus. ¿No existe la palabra?")

  # otras letras que tiene que haber en la palabra
  if (!is.null(estado$otras)) {
    tmp <- apply(res, 1, function(x) all(estado$otras %in% x))
    res <- res[tmp, , drop = FALSE]
  }

  res
}


evaluar_estado <- function(estado, candidata, target){
  if (length(target) == 1)
    target <- strsplit(target, "")[[1]]
  if (length(candidata) == 1)
    candidata <- strsplit(candidata, "")[[1]]

  for (i in 1:5)
    if (target[i] == candidata[i])
      estado$p[i] <- target[i]
    else estado$n[[i]] <- c(estado$n[[i]], candidata[i])

  matches <- intersect(candidata, target)
  estado$otras <- unique(c(estado$otras, matches))

  errores <- setdiff(candidata, target)
  estado$excluidas <- unique(c(estado$excluidas, errores))

  estado
}

# calcula el número promedio de palabras restantes
# interesa que sean las mínimas posibles
estimar_restantes <- function(candidata, corpus, estado){
  n_restantes <- sapply(1:nrow(corpus), function(i) {
    target_hipotetico <- corpus[i,]
    estado_hipotetico <- evaluar_estado(estado, candidata, target_hipotetico)
    restantes <- filtra_corpus(corpus, estado_hipotetico)
    nrow(restantes)
  })
  mean(n_restantes)
}

wordle_mv <- function(estado, corpus, popularidad = popularidad) {
  opciones <- filtra_corpus(corpus, estado)

  if (nrow(opciones) == 1){
    opciones <- data.frame(opciones)
    opciones$palabra <- row.names(opciones)
    return(opciones)
  }

  cat(paste0("   Quedan ", nrow(opciones), " opciones.\n"))
  cat("   Las más populares son:\n")

  tmp <- popularidad[popularidad$palabra %in% rownames(opciones), ]
  tmp <- tmp[order(-tmp$popularidad), ]
  print(head(tmp), row.names = FALSE)

  # si solo hay dos, devolver la más frecuente
  if (nrow(tmp) == 2)
    return(tmp)

  # si hay pocas opciones y una es mucho más corriente que el resto...
  if (nrow(tmp) <= 10){
    if (tmp$popularidad[1] > 5 * tmp$popularidad[2]) {
      return(tmp)
    }
  }

  if (nrow(opciones) > 100)
    opciones <- head(opciones, 100)

  # incluir nuevas opciones que puedan ser erróneas pero que partan muy bien

  tmp <- data.frame(table(opciones))

  otras_letras <- tmp[!tmp$opciones %in% estado$otras,]
  otras_letras <- otras_letras[order(otras_letras$Freq, decreasing = TRUE),]

  tmp <- data.frame(corpus)
  tmp$forma <- rownames(tmp)
  tmp <- melt(tmp, id.vars = "forma")
  tmp$variable <- NULL
  tmp <- unique(tmp)
  tmp <- merge(tmp, otras_letras, by.x = "value", by.y = "opciones")
  tmp <- ddply(tmp, .(forma), summarize, n = sum(Freq))
  tmp <- tmp[order(tmp$n, decreasing = T),]

  nuevas_opciones <- corpus[rownames(corpus) %in% head(tmp$forma, 20),]

  # merging both sources

  nuevas_opciones <- rbind(opciones, nuevas_opciones)

  verosimilitudes <- apply(nuevas_opciones, 1,
    function(x) estimar_restantes(x, opciones, estado))

  out <- data.frame(nuevas_opciones)
  out$verosimilitudes <- verosimilitudes
  out$palabra <- rownames(out)
  out <- merge(out, popularidad, by = "palabra")

  if (nrow(out) < 20) {
    out <- head(out[order(-out$popularidad), ], 3)
  }

  out <- out[order(out$verosimilitudes), ]

  head(out)
}


mi_estado <- list(
  # green/correct characters
  p  = character(5),
  # letters not in position i
  n = vector(mode = "list", length = 5),
  # otras letras que tiene que haber en la palabra
  otras = NULL,
  # letras que sabemos que no están
  excluidas = NULL
)

cat(paste0("Intento ", 1, "\n"))
cat(paste0("   Candidata: ", my_guess, "\n\n"))

mi_estado <- evaluar_estado(mi_estado, my_guess, my_target)

for (i in 1:6) {
  cat(paste0("Intento ", i+1, "\n"))
  candidata <- wordle_mv(mi_estado, my_corpus, popularidad)
  mi_candidata <- candidata$palabra[1]
  cat("   Candidata: ", mi_candidata, "\n\n")
  if (mi_candidata == my_target)
    break
  mi_estado <- evaluar_estado(mi_estado, mi_candidata, my_target)
}
