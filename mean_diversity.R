suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(ggplot2)
  library(ggridges)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript mean_diversity.R <input_folder> <output_png> [width] [height] [dpi]")
}
input_folder <- args[1]
output_png  <- args[2]
width       <- ifelse(length(args) >= 3, as.numeric(args[3]), 8)
height      <- ifelse(length(args) >= 4, as.numeric(args[4]), 5)
dpi         <- ifelse(length(args) >= 5, as.numeric(args[5]), 900)

read_all_models <- function(parent_dir) {
  model_dirs <- list.dirs(parent_dir, recursive = FALSE, full.names = TRUE)
  all_data_list <- list()
  empirical_div <- NA

  for (model_path in model_dirs) {
    model_name <- basename(model_path)
    sim_file <- file.path(model_path, "diversity_scores_bootstrapped_data.txt_gaps")
    pbr_file <- file.path(model_path, "diversity.pbr_gaps")

    if (file.exists(sim_file)) {
      df <- tryCatch({
        read.table(sim_file, header = TRUE, sep = "\t", stringsAsFactors = FALSE)
      }, error = function(e) {
        warning(paste("Failed to read:", sim_file))
        return(NULL)
      })

      if (!is.null(df)) {
        df$dataset <- model_name
        all_data_list[[model_name]] <- df
      }
    }

    if (is.na(empirical_div) && file.exists(pbr_file)) {
      line <- readLines(pbr_file)
      match <- grep("diversity original data", line, value = TRUE, ignore.case = TRUE)
      if (length(match) > 0) {
        empirical_div <- as.numeric(gsub(".*: ", "", match[1]))
      }
    }
  }

  combined_data <- bind_rows(all_data_list)

  combined_data <- combined_data %>%
    mutate(
      model_category = case_when(
        grepl("fix", dataset, ignore.case = TRUE) & grepl("PMSF", dataset, ignore.case = TRUE) ~ "fix_PMSF",
        grepl("opt", dataset, ignore.case = TRUE) & grepl("PMSF", dataset, ignore.case = TRUE) ~ "opt_PMSF",
        grepl("fix", dataset, ignore.case = TRUE) ~ "fix_noPMSF",
        grepl("opt", dataset, ignore.case = TRUE) ~ "opt_noPMSF",
        TRUE ~ "other"
      )
    )

  return(list(data = combined_data, empirical = empirical_div))
}

result <- read_all_models(input_folder)
combined_data <- result$data
empirical_div <- result$empirical

model_order <- combined_data %>%
  group_by(dataset) %>%
  summarise(mean_div = mean(diversity, na.rm = TRUE), .groups = "drop") %>%
  mutate(distance_to_empirical = abs(mean_div - empirical_div)) %>%
  arrange(distance_to_empirical) %>%
  pull(dataset)

combined_data <- combined_data %>%
  mutate(label = factor(dataset, levels = rev(model_order)))

color_palette <- c(
  "fix_noPMSF"  = "#9AC4DB",
  "opt_noPMSF"  = "#CB8D8B",
  "fix_PMSF"    = "#7BB661",
  "opt_PMSF"    = "#D4A373",
  "other"       = "grey70"
)

p <- ggplot(combined_data, aes(x = diversity, y = label, fill = model_category)) +
  geom_density_ridges(
    scale = 1.3, rel_min_height = 0, alpha = 0.7,
    color = "black", linewidth = 0.37,
    panel_scaling = FALSE, position = "identity"
  ) +
  geom_vline(xintercept = empirical_div, linetype = "dashed", color = "darkred", linewidth = 0.7) +
  scale_x_continuous(
    expand = c(0, 0),
    limits = c(
      min(combined_data$diversity, empirical_div, na.rm = TRUE),
      max(combined_data$diversity, empirical_div, na.rm = TRUE)
    )
  ) +
  scale_y_discrete(expand = expansion(add = c(0.3, 0.3))) +
  scale_fill_manual(
    values = color_palette,
    labels = c(
      "fix_noPMSF"  = "fix (no PMSF)",
      "opt_noPMSF"  = "opt (no PMSF)",
      "fix_PMSF"    = "fix (PMSF)",
      "opt_PMSF"    = "opt (PMSF)",
      "other"       = "other"
    )
  ) +
  labs(x = "Mean diversity", y = NULL) +
  theme_classic(base_size = 9) +
  theme(
    axis.title.x = element_text(size = 9),
    axis.text.x  = element_text(size = 8),
    axis.text.y  = element_text(size = 8),
    axis.ticks.y = element_line(linewidth = 0.4),
    axis.ticks.length.y = unit(2, "pt"),
    axis.line.x = element_line(linewidth = 0.5),
    axis.line.y = element_blank(),
    panel.grid.major.y = element_line(color = "grey85", linewidth = 0.3),
    panel.grid.major.x = element_blank(),
    legend.position = "top",
    legend.title = element_blank(),
    legend.text  = element_text(size = 7)
  )

ggsave(filename = output_png, plot = p, width = width, height = height, dpi = dpi)
cat(sprintf("Saved ridge plot to: %s\n", output_png))