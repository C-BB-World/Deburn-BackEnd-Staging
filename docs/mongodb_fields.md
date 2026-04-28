# Deburn MongoDB & Firebase Documentation

> Last updated: 2026-03-27

---

## Table of Contents

- [Database: `deburn` (Main)](#database-deburn-main)
- [Database: `deburn-hub`](#database-deburn-hub)
- [Firebase Authentication Analytics](#firebase-authentication-analytics)

---

## Database: `deburn` (Main)

**Cluster:** `cluster0.oxduzci.mongodb.net`

### `users` (65 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | Mongoose version key |
| `email` | str | User email (unique, indexed) |
| `passwordHash` | str | Hashed password |
| `organization` | str | Organization name |
| `country` | str | User country |
| `status` | str | Account status (e.g. `active`, `pending_verification`, `suspended`, `deleted`) |
| `profile` | object | |
| `profile.preferredLanguage` | str | |
| `profile.timezone` | str | |
| `emailVerification` | object | |
| `emailVerification.token` | str | Verification token |
| `emailVerification.expiresAt` | datetime | Token expiry |
| `passwordReset` | object | |
| `passwordReset.token` | str | Reset token |
| `passwordReset.expiresAt` | datetime | Token expiry |
| `consents` | object | GDPR consent tracking |
| `consents.dataProcessing` | object | `{ accepted, acceptedAt, version }` |
| `consents.marketing` | object | `{ accepted, acceptedAt }` |
| `consents.privacyPolicy` | object | `{ accepted, acceptedAt, version }` |
| `consents.termsOfService` | object | `{ accepted, acceptedAt, version }` |
| `coachExchanges` | object | |
| `coachExchanges.dailyCount` | int | Daily AI coach exchange count |
| `sessions` | array | Active session list |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `checkins` (264 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | Reference to user |
| `date` | str | Date string (YYYY-MM-DD) |
| `timestamp` | datetime | Submission time |
| `metrics` | object | |
| `metrics.mood` | int | 1-5 scale |
| `metrics.physicalEnergy` | int | 1-10 scale |
| `metrics.mentalEnergy` | int | 1-10 scale |
| `metrics.sleep` | int | 1-5 scale |
| `metrics.stress` | int | 1-10 scale |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

> Note: There is also a legacy `checkIns` collection (1 doc) with identical schema.

---

### `organizations` (2 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `name` | str | Organization name |
| `domain` | str | Email domain for matching |
| `status` | str | `active`, `suspended`, `deleted` |
| `createdBy` | ObjectId | User who created it |
| `settings` | object | |
| `settings.defaultMeetingDuration` | int | Minutes (default 60) |
| `settings.defaultGroupSize` | int | Default 4 |
| `settings.allowMemberPoolCreation` | bool | |
| `settings.timezone` | str | Default `Europe/Stockholm` |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `organizationmembers` (10 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `organizationId` | ObjectId | Reference to organization |
| `userId` | ObjectId | Reference to user |
| `role` | str | Member role |
| `status` | str | Membership status |
| `joinedAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

> Note: Legacy `organizationMembers` collection also exists (1 doc).

---

### `circlepools` (2 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `name` | str | Pool name |
| `topic` | str | Discussion topic |
| `description` | str | |
| `cadence` | str | Meeting frequency |
| `targetGroupSize` | int | Target group size |
| `status` | str | Pool status |
| `organizationId` | ObjectId | |
| `createdBy` | ObjectId | |
| `assignedAt` | datetime | When groups were assigned |
| `invitationSettings` | object | |
| `invitationSettings.expiryDays` | int | Invitation expiry in days |
| `stats` | object | |
| `stats.totalInvited` | int | |
| `stats.totalAccepted` | int | |
| `stats.totalDeclined` | int | |
| `stats.totalGroups` | int | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

> Note: Legacy `circlePools` collection also exists (1 doc, with additional `invitationSettings.customMessage` and `description` fields).

---

### `circlegroups` (8 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `name` | str | Group name |
| `poolId` | ObjectId | Reference to circle pool |
| `leaderId` | ObjectId/null | Group leader |
| `status` | str | |
| `members` | array of objects | |
| `members[].userId` | ObjectId | |
| `members[].name` | str | |
| `stats` | object | |
| `stats.meetingsHeld` | int | |
| `stats.totalMeetingMinutes` | int | |
| `stats.lastMeetingAt` | datetime/null | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `circleinvitations` (31 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `poolId` | ObjectId | |
| `email` | str | Invited email |
| `firstName` | str/null | |
| `lastName` | str/null | |
| `token` | str | Unique invitation token |
| `status` | str | `pending`, `accepted`, `declined` |
| `invitedBy` | ObjectId | |
| `userId` | ObjectId/null | Set when accepted |
| `emailSentAt` | datetime | |
| `emailSentCount` | int | |
| `lastReminderAt` | datetime/null | |
| `reminderCount` | int | |
| `expiresAt` | datetime | |
| `acceptedAt` | datetime/null | |
| `declinedAt` | datetime/null | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

> Note: Legacy `circleInvitations` collection also exists (1 doc).

---

### `circlemeetings` (32 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `groupId` | ObjectId | |
| `title` | str | |
| `description` | str/null | |
| `topic` | str/null | |
| `scheduledAt` | datetime | |
| `duration` | int | Minutes |
| `timezone` | str | |
| `meetingLink` | str | |
| `status` | str | |
| `scheduledBy` | ObjectId | |
| `attendees` | array of ObjectId | |
| `attendance` | array of objects | |
| `attendance[].userId` | ObjectId | |
| `attendance[].status` | str | |
| `attendance[].respondedAt` | datetime/null | |
| `calendarEvents` | array | Calendar integrations |
| `notes` | str/null | |
| `reminder24hSent` | bool | |
| `reminder1hSent` | bool | |
| `cancelledAt` | datetime/null | |
| `cancelledBy` | ObjectId/null | |
| `cancellationReason` | str/null | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `circlegroupmessages` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `groupId` | ObjectId | |
| `messages` | array of objects | |
| `messages[].messageId` | str | |
| `messages[].userId` | ObjectId | |
| `messages[].userName` | str | |
| `messages[].content` | str | |
| `messages[].encrypted` | bool | |
| `messages[].createdAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `conversations` (10 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `conversationId` | str | Unique conversation ID |
| `userId` | ObjectId | |
| `status` | str | |
| `topics` | array of str | |
| `messages` | array of objects | |
| `messages[].role` | str | `user` or `assistant` |
| `messages[].content` | str | |
| `messages[].metadata` | object | |
| `messages[].timestamp` | datetime | |
| `lastMessageAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `coachcommitments` (13 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `conversationId` | str | |
| `commitment` | str | The commitment text |
| `topic` | str | |
| `psychologicalTrigger` | str | |
| `reflectionQuestion` | str | |
| `circlePrompt` | str | |
| `followUpDate` | datetime | |
| `followUpCount` | int | |
| `status` | str | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

> Note: Legacy `coachCommitments` collection (33 docs) has additional fields: `completedAt`, `helpfulnessRating`, `lastFollowUpAt`, `reflectionNotes`, `trigger`.

---

### `coachsessions` (22 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `conversationId` | str | |
| `startedAt` | datetime | |

---

### `chatmessages` (4 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `conversationId` | str | |
| `role` | str | |
| `content` | str | |
| `metadata` | object | |
| `metadata.topics` | array | |
| `metadata.actions` | array | |
| `metadata.quickReplies` | array | |
| `createdAt` | datetime | |

---

### `contentitems` (44 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `titleEn` | str | English title |
| `category` | str | |
| `contentType` | str | |
| `purpose` | str | |
| `outcome` | str | |
| `status` | str | |
| `sortOrder` | int | |
| `coachEnabled` | bool | Available to AI coach |
| `coachPriority` | int | |
| `coachTopics` | array of str | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `contentviews` (151 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `contentId` | ObjectId | |
| `viewedAt` | datetime | |

---

### `contentratings` (2 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `contentId` | ObjectId | |
| `rating` | int | |
| `createdAt` | datetime | |

---

### `userpreferences` (69 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `userId` | ObjectId | |
| `coachPreferences` | object | |
| `coachPreferences.voice` | str | TTS voice preference |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `userlearningqueues` (58 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `queue` | array of str | Ordered content IDs |
| `currentIndex` | int | Current position in queue |
| `lastAdvancedDate` | str | Date string |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `useravailabilities` (7 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `groupId` | ObjectId | |
| `memberAvailability` | array of objects | |
| `memberAvailability[].userId` | ObjectId | |
| `memberAvailability[].name` | str | |
| `memberAvailability[].timezone` | str | |
| `memberAvailability[].updatedAt` | datetime | |
| `memberAvailability[].slots` | array of objects | |
| `memberAvailability[].slots[].date` | str | |
| `memberAvailability[].slots[].hour` | int | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `insights` (6 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `type` | str | Insight type |
| `trigger` | str | What triggered the insight |
| `title` | str | |
| `body` | str | |
| `isRead` | bool | |
| `expiresAt` | datetime/null | |
| `metrics` | object | |
| `metrics.streak` | object | `{ current, longest }` |
| `metrics.morningCheckIns` | int | |
| `metrics.lowEnergyDays` | int | |
| `metrics.sleepMoodCorrelation` | int | |
| `metrics.moodChange` | int/null | |
| `metrics.stressChange` | int/null | |
| `metrics.stressDayPattern` | str/null | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `notifications` (85 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `userId` | ObjectId | |
| `type` | str | Notification type |
| `title` | str | |
| `message` | str | |
| `read` | bool | |
| `readAt` | datetime/null | |
| `metadata` | object | Extra context (e.g. `poolId`, `fromGroupId`, `toGroupId`) |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `auditlogs` (241 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `userId` | ObjectId | |
| `action` | str | Action performed |
| `timestamp` | datetime | |
| `metadata` | object | |
| `metadata.email` | str | |
| `metadata.ipAddress` | str | |
| `metadata.userAgent` | str | |

> Note: Legacy `auditLogs` collection (52 docs) has additional `expiresAt` TTL field.

---

### `hubadmins` (4 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `email` | str | Admin email |
| `status` | str | |
| `addedBy` | str | |
| `addedAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `hubsettings` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `key` | str | Setting key |
| `dailyExchangeLimit` | int | Max daily AI exchanges |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `userBookmarks` (3 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `userId` | ObjectId | |
| `contentId` | str | |
| `bookmarkedAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `videoprojects` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `titleEn` | str | |
| `titleSv` | str | |
| `status` | str | |
| `currentStep` | str | |
| `purpose` | str | |
| `language` | str | |
| `scriptText` | str | |
| `error` | str | |
| `projectPath` | str | |
| `finalVideoPath` | str | |
| `finalVideoPathSv` | str | |
| `mixedAudioPath` | str | |
| `mixedAudioPathSv` | str | |
| `scenes` | array of objects | Complex scene data with narration, images, audio, templates |
| `imageSettings` | object | `{ aspectRatio, model, style }` |
| `videoSettings` | object | `{ fps, width, height, preset, fadeDuration, kenBurnsEnabled, aiAnimationEnabled }` |
| `voiceSettings` | object | `{ voiceId, voiceName, modelId, stability, similarityBoost }` |
| `musicSettings` | object | `{ musicTrack, musicFolder, volumes, fade settings }` |
| `textSettings` | object | `{ font, colors, positioning, background }` |
| `estimatedCost` | object | `{ audio, images, total }` |
| `youtube` | object | `{ videoIdEn, videoIdSv, urlEn, urlSv, embedCodes, status, uploadedAt }` |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `videojobs` (83 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `projectId` | ObjectId | |
| `type` | str | Job type |
| `status` | str | |
| `progress` | int | 0-100 |
| `currentScene` | int | |
| `totalScenes` | int | |
| `error` | str | |
| `logs` | array of objects | `{ message, timestamp }` |
| `startedAt` | datetime | |
| `completedAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `youtubeconnections` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `userId` | ObjectId | |
| `channelId` | str | |
| `channelTitle` | str | |
| `tokens` | object | `{ access_token, refresh_token, expiry_date }` |
| `connectedAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### Empty Collections

| Collection | Documents |
|------------|-----------|
| `calendarconnections` | 0 |
| `circlemessages` | 0 |
| `feedbacks` | 0 |
| `userlearning` | 0 |

---

---

## Database: `deburn-hub`

**Cluster:** `cluster0.oxduzci.mongodb.net`

### `conversations` (75 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `conversationId` | str | |
| `userId` | ObjectId | |
| `status` | str | |
| `topics` | array of str | |
| `messages` | array of objects | |
| `messages[].role` | str | |
| `messages[].content` | str | |
| `messages[].encrypted` | bool | |
| `messages[].metadata` | object | |
| `messages[].timestamp` | datetime | |
| `lastMessageAt` | datetime | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `aiprompt` (3 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `promptType` | str | |
| `component` | str | |
| `content` | object | |
| `content.en` | str | English prompt text |
| `content.sv` | str | Swedish prompt text |
| `isActive` | bool | |
| `order` | int | |
| `version` | int | |
| `metadata` | object | |
| `metadata.description` | str | |
| `metadata.lastEditedBy` | str | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `contentitems` (61 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `titleEn` | str | |
| `titleSv` | str | |
| `category` | str | |
| `contentType` | str | |
| `purpose` | str | |
| `outcome` | str | |
| `textContentEn` | str | Full English text content |
| `textContentSv` | str | Full Swedish text content |
| `status` | str | |
| `sortOrder` | int | |
| `lengthMinutes` | int | |
| `ttsVoice` | str | |
| `ttsSpeed` | int | |
| `coachEnabled` | bool | |
| `coachPriority` | int | |
| `coachTopics` | array | |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `feedback` (11 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `userId` | str | |
| `userName` | str | |
| `content` | str | Feedback text |
| `rating` | int | |
| `isAnonymous` | bool | |
| `createdAt` | datetime | |

---

### `learningfeedback` (8 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `contentId` | str | |
| `contentTitle` | str | |
| `totalRatings` | int | |
| `ratings` | array of objects | |
| `ratings[].userId` | str | |
| `ratings[].rating` | int | |
| `ratings[].isAnonymous` | bool | |
| `ratings[].createdAt` | datetime | |

---

### `reminders` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `name` | str | Reminder name |
| `published` | bool | |
| `recipients` | array | |
| `content` | object | |
| `content.en` | object | `{ subject, header, body, buttonText, buttonUrl, closing, signOff }` |
| `content.sv` | object | `{ subject, header, body, buttonText, buttonUrl, closing, signOff }` |
| `schedule` | object | |
| `schedule.frequency` | str | |
| `schedule.cronExpression` | str | |
| `schedule.hour` | int | |
| `schedule.minute` | int | |
| `schedule.dayOfMonth` | int | |
| `schedule.sendDays` | array | |
| `sendCount` | int | |
| `lastSentAt` | datetime | |
| `updatedAt` | datetime | |

---

### `contact_submissions` (1 document)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `name` | str | |
| `email` | str | |
| `company` | str | |
| `message` | str | |
| `ip` | str | Submitter IP |
| `createdAt` | datetime | |

---

### `hubadmins` (4 documents)

Same schema as main database `hubadmins`.

### `hubsettings` (1 document)

Same schema as main database `hubsettings`.

---

### GridFS Collections (File Storage)

| Collection | Documents | Purpose |
|------------|-----------|---------|
| `audio.files` | 46 | Audio file metadata (TTS narrations) |
| `audio.chunks` | 999 | Audio binary data |
| `images.files` | 13 | Image file metadata |
| `images.chunks` | 71 | Image binary data |
| `video.files` | 18 | Video file metadata |
| `video.chunks` | 166 | Video binary data |
| `musics` | 37 | Background music tracks |

#### `audio.files` / `images.files` / `video.files` metadata

| Field | Type |
|-------|------|
| `metadata.contentItemId` | str |
| `metadata.contentType` | str |
| `metadata.language` | str |
| `metadata.title` | str |
| `metadata.uploadedAt` | datetime |
| `metadata.originalPath` | str |
| `metadata.projectId` | str |
| `metadata.sceneNumber` | int |

#### `musics` (37 documents)

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | |
| `__v` | int | |
| `displayName` | str | |
| `originalFilename` | str | |
| `folder` | str | Category folder |
| `mimeType` | str | |
| `fileSize` | int | |
| `duration` | float | Seconds |
| `audioData` | bytes | Binary audio data |
| `createdAt` | datetime | |
| `updatedAt` | datetime | |

---

### `videoprojects` (hub) (1 document)

Simplified version of main db's `videoprojects` (without text/voice/youtube settings).

### `videojobs` (hub) (0 documents)

Empty collection.

---

---

## Firebase Authentication Analytics

**Project:** `projectdeburn-62593`

### Summary (as of 2026-03-27)

| Metric | Count |
|--------|-------|
| **Total users registered** | **51** |
| Email verified | 42 |
| Email NOT verified | 9 |
| **Active accounts** (not disabled) | **13** |
| Disabled accounts | 38 |
| Never signed in | 4 |
| **Signed in (last 30 days)** | **32** |
| Auth provider | `password` (all 51 users) |

### Active Users (not disabled)

| Email | Verified | Created | Last Login |
|-------|----------|---------|------------|
| cbbank.world@gmail.com | No | 2026-01-15 | 2026-03-03 |
| christopher.brainbank@gmail.com | Yes | 2026-01-18 | 2026-02-02 |
| christopher.sastropranoto@gmail.com | Yes | 2026-01-15 | 2026-03-12 |
| christopher.sastropranoto@outlook.com | Yes | 2026-02-02 | 2026-02-02 |
| alexandra@franklincovey.no | Yes | 2026-02-02 | 2026-03-06 |
| vladimirzedong7@gmail.com | Yes | 2026-02-01 | 2026-02-01 |
| operator@brainbank.world | No | 2026-01-26 | 2026-01-27 |
| hms.gack@gmail.com | No | 2026-01-26 | Never |
| wennerholmalexandra@gmail.com | No | 2026-01-22 | 2026-03-23 |
| dsdemario1@gmail.com | Yes | 2026-01-26 | 2026-03-03 |
| gcakush@gmail.com | No | 2026-01-26 | 2026-03-02 |
| demo@brainbank.world | Yes | 2026-03-12 | 2026-03-20 |
| hola@energyismedicine.com.au | Yes | 2026-03-24 | 2026-03-24 |

### Disabled Users (38 accounts)

| Email | Verified | Created | Last Login |
|-------|----------|---------|------------|
| jacob95nilsson@hotmail.com | Yes | 2026-02-06 | 2026-03-16 |
| luisachtu@gmail.com | No | 2026-02-06 | 2026-02-06 |
| mjshastsport@gmail.com | Yes | 2026-02-06 | 2026-03-11 |
| karin.petermann@xylem.com | Yes | 2026-02-27 | 2026-02-27 |
| karolak.p45@gmail.com | Yes | 2026-03-06 | 2026-03-07 |
| tinat@pc2000.se | Yes | 2026-03-02 | Never |
| roger.bard@hotmail.se | Yes | 2026-02-03 | 2026-03-13 |
| robin.zickbauer@gmail.com | Yes | 2026-02-03 | 2026-02-03 |
| milton.albinson@gmail.com | Yes | 2026-02-06 | 2026-03-10 |
| arsimhasani99@gmail.com | Yes | 2026-02-03 | 2026-02-23 |
| peterhaman2012@gmail.com | Yes | 2026-03-03 | 2026-03-17 |
| cheryl@cocolab.cc | Yes | 2026-02-20 | Never |
| androlss@hotmail.com | Yes | 2026-02-03 | 2026-03-13 |
| vejlgaard@advize.one | Yes | 2026-03-04 | 2026-03-04 |
| patrik.enarsson@avaloninnovation.com | Yes | 2026-02-06 | 2026-02-06 |
| patrik.enarsson@outlook.com | Yes | 2026-02-06 | 2026-03-09 |
| alexandros.skold@hotmail.com | Yes | 2026-02-03 | 2026-03-05 |
| carina@synergize.se | Yes | 2026-02-23 | 2026-02-23 |
| omar.hams@hotmail.se | No | 2026-02-03 | 2026-03-17 |
| omar.hams@hotmail.com | Yes | 2026-02-03 | 2026-02-03 |
| johan_aberg78@hotmail.com | Yes | 2026-02-03 | 2026-03-11 |
| johanbrengesjo@gmail.com | Yes | 2026-02-05 | 2026-03-19 |
| sm7rrf@gmail.com | Yes | 2026-02-05 | 2026-03-06 |
| maja.stenberg@volvocars.com | Yes | 2026-02-18 | 2026-02-18 |
| dekki80@hotmail.com | Yes | 2026-02-03 | 2026-03-13 |
| fredrik@efea.se | Yes | 2026-02-20 | 2026-02-20 |
| tgh@releaser.dk | Yes | 2026-03-03 | 2026-03-03 |
| andreas.hindriksson@tarkett.com | Yes | 2026-02-09 | 2026-03-12 |
| satu.lohilahti-jonsson@holtab.se | Yes | 2026-02-09 | 2026-02-09 |
| stoffifee84@gmail.com | No | 2026-02-06 | 2026-02-06 |
| liselott.wentzel@almi.se | Yes | 2026-03-06 | 2026-03-06 |
| krviberg@gmail.com | Yes | 2026-02-06 | 2026-03-18 |
| marielle.humanfirstai@gmail.com | Yes | 2026-01-28 | 2026-03-02 |
| maria.strand@aak.com | No | 2026-03-19 | Never |
| celarjelena@gmail.com | Yes | 2026-02-26 | 2026-02-26 |
| lenny.fasth@hotmail.com | Yes | 2026-02-06 | 2026-03-04 |
| jonas.siebert@nkt.com | Yes | 2026-02-20 | 2026-02-20 |
| patrick.isacson@eneriq.se | Yes | 2026-02-02 | 2026-03-09 |
