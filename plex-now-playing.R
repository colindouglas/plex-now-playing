# Set working directory (ending with /) where it can save tokens, find credentials.
# NOTE: Password will be saved in plaintext in this folder! Choose somewhere secure.
wkdir <- "~/Scripts/"
# It should contain a file called ".plex_creds" that is your Plex username and password, separated by a comma

############ To automatically write the .plex_creds file, modify and uncomment the following lines
############ This only needs to be done once, then lines can be re-commented afterwards 
# write.table(data.frame("username" = "John_k_User", "password" = "hunter2"), 
#   file = paste0(wkdir, ".plex_creds"), col.names = FALSE, row.names = FALSE, sep = ",")

# Load the necessary packages
packages <- c("dplyr", "tibble", "httr", "readr", "tidyr", "stringr")
if (!all(unlist(lapply(packages, require, character.only = TRUE)))) {
  install.packages(packages)
  lapply(packages, require, character.only = TRUE)
}

# Set the path to the credentials and the auth token
credential_path <- paste0(wkdir, ".plex_creds")
token_path <- paste0(wkdir, ".plex_token")

token <- tryCatch({
  read_csv(token_path)
}, error = function(x) NULL)

if (!length(token) | token$authed_at < Sys.Date()) {
  
  credentials <- read_csv(credential_path, col_names = FALSE)
  token_response <- content(
    POST(
      url = "https://plex.tv/users/sign_in.json", 
      body = paste0("user%5Blogin%5D=", credentials[[1]], "&user%5Bpassword%5D=", credentials[[2]]), 
      add_headers("X-Plex-Client-Identifier" = "NowPlayingScript", 
                  "X-Plex-Product" = "NowPlayingScript",
                  "X-Plex-Version" = "0.0.1")
    )
  )
  
  if (length(token_response$error)) {
    cat("Error getting authentication token! Check Plex credentials")
    quit(status = 1)
  }

  token <- token_response %>% 
    tibble(object = .) %>% 
    unnest_wider(object) %>%
    select(-subscription, -roles) %>% 
    add_column(authed_at = Sys.Date())
  
  write_csv(tr_df, path = token_path) 
  
}

token <- token$authToken


now_playing <- content(GET("http://127.0.0.1:32400/status/sessions", add_headers("X-Plex-Token" = token)))

if (!is.null(now_playing$MediaContainer$Metadata)) {
  np_nested <- tibble(metadata = now_playing$MediaContainer$Metadata) %>%
    unnest_wider(metadata) %>%
    unnest_wider(User, names_sep = ".")
  
  # If there's no "last viewed at" time, use the current time
  if (is.null(np_nested$lastViewedAt)) np_nested$lastViewedAt <- as.numeric(Sys.time())
  
  current <- np_nested %>%
    rowwise() %>%
    mutate(episode = paste0("S", gsub("[A-Za-z ]+", "", parentTitle), "E", str_pad(index, 2, pad = "0"))) %>%
    select(user = User.title,
           series = grandparentTitle,
           ep_name = title,
           time = lastViewedAt,
           episode)
  
  print_pretty <- function(df, row) {
    time <- as.numeric(df$time[row]) %>% 
      as.POSIXct(origin = "1970-01-01", tz = Sys.timezone()) %>% 
      format("%b %d, %I:%M%P")
    paste0(time, ": ", df$user[row], " // ", df$series[row], " - ", df$episode[row], " - ", df$ep_name[row])
  }
  
  for (i in 1:nrow(current)) {
    cat(print_pretty(current, i))
    cat("\n")
  }
} else {
  cat("Nothing playing")
}