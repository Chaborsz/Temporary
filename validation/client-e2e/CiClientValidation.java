package validation;

import dev.companion.minecraft.CompanionEntity;
import dev.companion.minecraft.CompanionCombatMode;
import dev.companion.minecraft.CompanionOrder;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.mob.ZombieEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.entity.EquipmentSlot;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.text.Text;
import net.minecraft.util.math.Box;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.world.CreateWorldScreen;
import net.minecraft.client.option.Perspective;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Comparator;
import java.lang.reflect.Method;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

/** Temporary CI-only observer for the real integrated client/server path. */
public final class CiClientValidation implements ModInitializer, ClientModInitializer {
    private static final AtomicBoolean worldCreationRequested = new AtomicBoolean();
    private static final AtomicBoolean worldCreationStarted = new AtomicBoolean();
    private static final AtomicBoolean worldAnnounced = new AtomicBoolean();
    private static final AtomicBoolean summonSent = new AtomicBoolean();
    private static final AtomicBoolean testArenaPrepared = new AtomicBoolean();
    private static int testArenaWarmupTicks;
    private static final AtomicBoolean companionAnnounced = new AtomicBoolean();
    private static final AtomicBoolean attackerSent = new AtomicBoolean();
    private static final AtomicBoolean uiReadyAnnounced = new AtomicBoolean();
    private static final AtomicBoolean passAnnounced = new AtomicBoolean();
    private static UUID ownerUuid;
    private static UUID zombieUuid;
    private static UUID companionUuid;
    private static int serverTicks;
    private static int targetStableTicks;
    private static int ownerStableTicks;
    private static float initialZombieHealth = -1.0F;
    private static float previousOwnerHealth = Float.NaN;
    private static boolean ownerTestSetup;
    private static boolean zombieDisappearanceAnnounced;
    private static UUID lastLoggedDamageUuid;
    private static float lastLoggedZombieHealth = Float.NaN;
    private static UUID swordDamageUuid;
    private static float lastSwordZombieHealth = Float.NaN;
    private static boolean ownerTookZombieDamage;
    private static boolean companionAcquiredZombie;
    private static boolean navigationStarted;
    private static boolean companionDamagedZombie;
    private static boolean targetSurvivedTwoTicks;
    private static boolean followResumed;
    private static boolean failed;
    private static String lastClientSwingPhase = "";
    private static boolean clientSwingObserved;

    @Override
    public void onInitialize() {
        trace("CI_COMMON_ENTRYPOINT_READY");
    }

    @Override
    public void onInitializeClient() {
        trace("CI_HARNESS_READY");
        ServerTickEvents.END_SERVER_TICK.register(CiClientValidation::serverTick);
        ClientTickEvents.END_CLIENT_TICK.register(CiClientValidation::clientTick);
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> dispatcher.register(
                CommandManager.literal("cihud").requires(source -> source.hasPermissionLevel(2))
                        .then(CommandManager.literal("full").executes(context -> setHud(context.getSource().getServer(), 24.0F, 20)))
                        .then(CommandManager.literal("partial").executes(context -> setHud(context.getSource().getServer(), 23.0F, 19)))
                        .then(CommandManager.literal("empty").executes(context -> setHud(context.getSource().getServer(), 12.0F, 10)))
                        .then(CommandManager.literal("critical").executes(context -> setHud(context.getSource().getServer(), 1.0F, 1)))));
    }

    private static int setHud(MinecraftServer server, float health, int food) {
        ServerPlayerEntity owner = server.getPlayerManager().getPlayerList().stream().findFirst().orElse(null);
        CompanionEntity companion = findOwnedCompanion(owner);
        if (companion == null) return 0;
        companion.setHealth(health);
        try {
            var method = CompanionEntity.class.getDeclaredMethod("setFoodForTesting", int.class, float.class, float.class);
            method.setAccessible(true);
            method.invoke(companion, food, (float) food, 0.0F);
        } catch (ReflectiveOperationException failure) {
            trace("CI_HUD_STATE_ERROR " + failure);
            return 0;
        }
        trace("CI_HUD_STATE health=" + health + " food=" + food);
        return 1;
    }

    private static void ensureIntegratedWorld(MinecraftClient client) {
        if (client.currentScreen instanceof CreateWorldScreen createScreen) {
            if (worldCreationStarted.compareAndSet(false, true)) {
                try {
                    createScreen.getWorldCreator().setCheatsEnabled(true);
                    Method createLevel = CreateWorldScreen.class.getDeclaredMethod("createLevel");
                    createLevel.setAccessible(true);
                    createLevel.invoke(createScreen);
                    trace("CI_INTEGRATED_WORLD_CREATE_STARTED cheats=true");
                } catch (ReflectiveOperationException failure) {
                    trace("CI_INTEGRATED_WORLD_CREATE_FAILURE " + failure);
                    throw new IllegalStateException("Could not start the CI integrated test world", failure);
                }
            }
            return;
        }
        if (worldCreationRequested.compareAndSet(false, true)) {
            CreateWorldScreen.create(client, client.currentScreen);
            trace("CI_INTEGRATED_WORLD_CREATE_SCREEN_REQUESTED");
        }
    }

    private static void clientTick(MinecraftClient client) {
        if (client.player == null && client.world == null) {
            ensureIntegratedWorld(client);
        }
        if (client.player == null || client.world == null || client.getNetworkHandler() == null) {
            worldAnnounced.set(false);
            return;
        }
        if (worldAnnounced.compareAndSet(false, true)) {
            ownerUuid = client.player.getUuid();
            trace("CI_WORLD_READY player=" + ownerUuid + " world=" + client.world.getRegistryKey().getValue());
        }
        if (!summonSent.get()) {
            boolean stableWorld = client.player.isOnGround()
                    && client.world.isChunkLoaded(client.player.getBlockPos())
                    && client.player.age > 40;
            ownerStableTicks = stableWorld ? ownerStableTicks + 1 : 0;
            if (ownerStableTicks >= 40 && testArenaPrepared.compareAndSet(false, true)) {
                client.getNetworkHandler().sendChatCommand("gamemode survival");
                client.getNetworkHandler().sendChatCommand("difficulty normal");
                client.getNetworkHandler().sendChatCommand("fill ~-16 ~ ~-16 ~16 ~2 ~16 minecraft:air");
                client.getNetworkHandler().sendChatCommand("fill ~-16 ~-1 ~-16 ~16 ~-1 ~16 minecraft:stone");
                trace("CI_TEST_ARENA_PREPARED center=" + client.player.getBlockPos());
            } else if (testArenaPrepared.get() && !summonSent.get()) {
                if (++testArenaWarmupTicks >= 20) {
                    summonSent.set(true);
                    client.getNetworkHandler().sendChatCommand("companion summon");
                    trace("CI_PRODUCTION_SUMMON_SENT groundedTicks=" + ownerStableTicks
                            + " playerAge=" + client.player.age + " pos=" + client.player.getBlockPos());
                }
            }
        }
        // Owner UUID is server-owned NBT state and is not a vanilla spawn field. Discover the
        // replicated entity by type/range here; serverTick independently verifies its owner.
        CompanionEntity companion = client.world.getEntitiesByClass(CompanionEntity.class,
                        client.player.getBoundingBox().expand(64.0D), Entity::isAlive)
                .stream().min(Comparator.comparingDouble(entity -> entity.squaredDistanceTo(client.player))).orElse(null);
        if (companion != null) {
            float progress = companion.getHandSwingProgress(1.0F);
            String phase;
            if (!companion.handSwinging) {
                phase = clientSwingObserved ? "IDLE_AGAIN" : "IDLE";
                clientSwingObserved = false;
            } else {
                clientSwingObserved = true;
                phase = progress < 0.25F ? "EARLY" : progress < 0.70F ? "MID" : "LATE";
            }
            if (!phase.equals(lastClientSwingPhase)) {
                lastClientSwingPhase = phase;
                trace("CI_RENDER_SWING_PHASE phase=" + phase + " progress=" + progress
                        + " handSwingTicks=" + companion.handSwingTicks
                        + " model=" + companion.getModelVariant().name()
                        + " weapon=" + companion.getEquippedStack(EquipmentSlot.MAINHAND).getItem()
                        + " chest=" + companion.getEquippedStack(EquipmentSlot.CHEST).getItem()
                        + " head=" + companion.getEquippedStack(EquipmentSlot.HEAD).getItem());
            }
        }
        if (companion != null && companionAnnounced.compareAndSet(false, true)) {
            companionUuid = companion.getUuid();
            client.options.setPerspective(Perspective.THIRD_PERSON_BACK);
            client.player.lookAt(EntityAnchorArgumentTypeCompat.EYES, companion.getEyePos());
            trace("CI_COMPANION_SYNCED uuid=" + companionUuid + " mode=" + companion.getCombatMode()
                    + " order=" + companion.getOrder() + " clientOwnerField=" + companion.getOwnerUuid()
                    + " distance=" + companion.distanceTo(client.player));
        }
        if (companion != null && Files.exists(uiCompletePath())
                && companion.getCombatMode() == CompanionCombatMode.DEFENSIVE
                && companion.getOrder() == CompanionOrder.FOLLOW
                && attackerSent.compareAndSet(false, true)) {
            client.getNetworkHandler().sendChatCommand("gamemode survival");
            client.getNetworkHandler().sendChatCommand("time set midnight");
            // Keep the real hostile near the Companion while leaving it close enough to
            // acquire and damage the owner. This gives retaliation a fair pathing window and
            // changes only world geometry; it never writes a target or threat into mod state.
            client.getNetworkHandler().sendChatCommand("tp @e[type=minecraft_companion:companion,limit=1,sort=nearest] ~8 ~ ~");
            client.getNetworkHandler().sendChatCommand("summon minecraft:zombie ~-5 ~ ~ {PersistenceRequired:1b}");
            trace("CI_REAL_ZOMBIE_SPAWN_COMMAND_SENT");
        }
    }

    private static void serverTick(MinecraftServer server) {
        if (failed) return;
        serverTicks++;
        ServerPlayerEntity owner = ownerUuid == null ? server.getPlayerManager().getPlayerList().stream()
                .findFirst().orElse(null) : server.getPlayerManager().getPlayer(ownerUuid);
        if (owner == null) return;
        float ownerHealth = owner.getHealth();
        if (Float.isNaN(previousOwnerHealth)) previousOwnerHealth = ownerHealth;
        if (ownerHealth < previousOwnerHealth) {
            Entity attacker = owner.getAttacker();
            if (attacker instanceof ZombieEntity zombie) {
                ownerUuid = owner.getUuid();
                zombieUuid = zombie.getUuid();
                ownerTookZombieDamage = true;
                trace("CI_OWNER_DAMAGE accepted=true player=" + owner.getUuid() + " zombie=" + zombie.getUuid()
                        + " attacker=" + attacker.getType() + " health=" + previousOwnerHealth + "->" + ownerHealth);
            }
        }
        previousOwnerHealth = ownerHealth;
        if (summonSent.get() && serverTicks % 40 == 0) {
            var nearbyCompanions = owner.getWorld().getEntitiesByClass(CompanionEntity.class,
                    owner.getBoundingBox().expand(64.0D), Entity::isAlive);
            trace("CI_SERVER_SPAWN_DIAGNOSTIC owner=" + owner.getUuid() + " nearby=" + nearbyCompanions.size());
            for (CompanionEntity observed : nearbyCompanions) {
                trace("CI_SERVER_COMPANION uuid=" + observed.getUuid() + " owner=" + observed.getOwnerUuid()
                        + " alive=" + observed.isAlive() + " distance=" + observed.distanceTo(owner)
                        + " ownerMatch=" + owner.getUuid().equals(observed.getOwnerUuid()));
            }
        }
        CompanionEntity companion = findOwnedCompanion(owner);
        if (companion == null) return;
        if (passAnnounced.get()) {
            var visualTargets = owner.getWorld().getEntitiesByClass(ZombieEntity.class,
                    owner.getBoundingBox().expand(24.0D), Entity::isAlive);
            for (ZombieEntity target : visualTargets) {
                if (target.getUuid().equals(zombieUuid) || target.getHealth() >= target.getMaxHealth()
                        || target.getAttacker() != companion) continue;
                if (!target.getUuid().equals(swordDamageUuid)
                        || target.getHealth() < lastSwordZombieHealth - 0.01F) {
                    swordDamageUuid = target.getUuid();
                    lastSwordZombieHealth = target.getHealth();
                    trace("CI_COMPANION_DAMAGE zombie=" + target.getUuid() + " companion=" + companion.getUuid()
                            + " weapon=" + net.minecraft.registry.Registries.ITEM.getId(
                            companion.getEquippedStack(EquipmentSlot.MAINHAND).getItem())
                            + " model=" + companion.getModelVariant() + " health=" + target.getHealth());
                }
            }
            return;
        }
        if (zombieUuid != null) {
            ZombieEntity damagedZombie = findZombie((ServerWorld) owner.getWorld(), zombieUuid);
            if (damagedZombie != null && damagedZombie.getHealth() < damagedZombie.getMaxHealth()
                    && companionUuid != null) {
                Entity damageSource = damagedZombie.getAttacker();
                if (damageSource instanceof CompanionEntity && damageSource.getUuid().equals(companionUuid)) {
                    companionDamagedZombie = true;
                    if (!damagedZombie.getUuid().equals(lastLoggedDamageUuid)
                            || damagedZombie.getHealth() < lastLoggedZombieHealth - 0.01F) {
                        lastLoggedDamageUuid = damagedZombie.getUuid();
                        lastLoggedZombieHealth = damagedZombie.getHealth();
                        trace("CI_COMPANION_DAMAGE zombie=" + damagedZombie.getUuid() + " companion=" + companionUuid
                                + " weapon=" + net.minecraft.registry.Registries.ITEM.getId(
                                companion.getEquippedStack(EquipmentSlot.MAINHAND).getItem())
                                + " health=" + damagedZombie.getHealth());
                    }
                }
            }
        }
        if (companionUuid == null) companionUuid = companion.getUuid();
        if (attackerSent.get() && !uiReadyAnnounced.get()) {
            uiReadyAnnounced.set(true);
            trace("CI_SERVER_UI_STATE mode=" + companion.getCombatMode() + " order=" + companion.getOrder()
                    + " owner=" + companion.getOwnerUuid() + " player=" + owner.getUuid());
            if (companion.getCombatMode() != CompanionCombatMode.DEFENSIVE
                    || companion.getOrder() != CompanionOrder.FOLLOW) {
                failed = true;
                trace("CI_OWNER_DEFENSE_E2E_FAIL UI selection did not reach server DEFENSIVE/FOLLOW state");
                return;
            }
        }
        ZombieEntity zombie = zombieUuid == null ? owner.getWorld().getEntitiesByClass(ZombieEntity.class,
                        owner.getBoundingBox().expand(24.0D), Entity::isAlive).stream()
                .min(Comparator.comparingDouble(entity -> entity.squaredDistanceTo(owner))).orElse(null)
                : findZombie((ServerWorld) owner.getWorld(), zombieUuid);
        if (zombie != null) {
            if (zombieUuid == null) zombieUuid = zombie.getUuid();
            if (initialZombieHealth < 0.0F) {
                initialZombieHealth = zombie.getHealth();
                trace("CI_ZOMBIE_ACQUIRED uuid=" + zombie.getUuid() + " distanceOwner=" + zombie.distanceTo(owner)
                        + " distanceCompanion=" + companion.distanceTo(zombie) + " health=" + initialZombieHealth);
            }
            if (attackerSent.get() && serverTicks % 20 == 0) {
                trace("CI_ZOMBIE_STATE uuid=" + zombie.getUuid() + " alive=" + zombie.isAlive()
                        + " health=" + zombie.getHealth() + " target=" + (zombie.getTarget() == null ? "null" : zombie.getTarget().getUuid())
                        + " ownerHealth=" + owner.getHealth() + " ownerGameMode=" + owner.interactionManager.getGameMode()
                        + " difficulty=" + owner.getWorld().getDifficulty());
            }
            if (ownerTookZombieDamage && zombie.getUuid().equals(zombieUuid)) {
                if (companion.getTarget() == zombie) {
                    if (!companionAcquiredZombie) {
                        companionAcquiredZombie = true;
                        trace("CI_TARGET_ACQUIRED player=" + owner.getUuid() + " owner=" + companion.getOwnerUuid()
                                + " companion=" + companion.getUuid() + " zombie=" + zombie.getUuid()
                                + " dimension=" + owner.getWorld().getRegistryKey().getValue()
                                + " distance=" + companion.distanceTo(zombie) + " mode=" + companion.getCombatMode()
                                + " order=" + companion.getOrder());
                    }
                    targetStableTicks++;
                    if (!companion.getNavigation().isIdle() && !navigationStarted) {
                        navigationStarted = true;
                        trace("CI_NAVIGATION_STARTED distance=" + companion.distanceTo(zombie));
                    }
                    if (targetStableTicks >= 3) targetSurvivedTwoTicks = true;
                }
            }
        }
        if (ownerTookZombieDamage && companionAcquiredZombie && companionDamagedZombie
                && (zombie == null || zombie.isDead() || companion.getTarget() == null)) {
            followResumed = companion.getOrder() == CompanionOrder.FOLLOW;
        }
        if (attackerSent.get() && zombieUuid != null && zombie == null && !zombieDisappearanceAnnounced) {
            zombieDisappearanceAnnounced = true;
            trace("CI_ZOMBIE_DISAPPEARED uuid=" + zombieUuid + " ownerHealth=" + owner.getHealth()
                    + " ownerAttacker=" + owner.getAttacker() + " companionTarget=" + companion.getTarget());
        }
        if (ownerTookZombieDamage && companionAcquiredZombie && navigationStarted
                && targetSurvivedTwoTicks && companionDamagedZombie && followResumed) {
            passAnnounced.set(true);
            trace("CI_OWNER_DEFENSE_E2E_PASS ownerDamage=true target=true targetStableTicks=" + targetStableTicks
                    + " navigation=true companionMeleeDamage=true followResumed=true");
            return;
        }
        if (serverTicks > 1800 && attackerSent.get()) {
            failed = true;
            trace("CI_OWNER_DEFENSE_E2E_FAIL ownerDamage=" + ownerTookZombieDamage + " target=" + companionAcquiredZombie
                    + " targetStableTicks=" + targetStableTicks + " navigation=" + navigationStarted
                    + " companionMeleeDamage=" + companionDamagedZombie + " followResumed=" + followResumed
                    + " player=" + owner.getUuid() + " companionOwner=" + companion.getOwnerUuid()
                    + " companion=" + companion.getUuid() + " zombie=" + zombieUuid + " currentTarget=" + companion.getTarget()
                    + " ownerHealth=" + owner.getHealth() + " ownerGameMode=" + owner.interactionManager.getGameMode()
                    + " difficulty=" + owner.getWorld().getDifficulty());
        }
    }

    private static CompanionEntity findOwnedCompanion(PlayerEntity owner) {
        if (owner == null) return null;
        return owner.getWorld().getEntitiesByClass(CompanionEntity.class, owner.getBoundingBox().expand(64.0D),
                entity -> owner.getUuid().equals(entity.getOwnerUuid())).stream()
                .min(Comparator.comparingDouble(entity -> entity.squaredDistanceTo(owner))).orElse(null);
    }

    private static ZombieEntity findZombie(ServerWorld world, UUID uuid) {
        Entity entity = world.getEntity(uuid);
        return entity instanceof ZombieEntity zombie ? zombie : null;
    }

    private static Path outputPath() {
        return Path.of(System.getenv().getOrDefault("CI_VALIDATION_DIR", "build/ci-validation"));
    }

    private static Path uiCompletePath() {
        return outputPath().resolve("ui-complete");
    }

    private static synchronized void trace(String message) {
        String line = "[CompanionClientE2E] " + message;
        System.out.println(line);
        try {
            Path dir = outputPath();
            Files.createDirectories(dir);
            Files.writeString(dir.resolve("runtime-trace.log"), line + System.lineSeparator(),
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException ignored) {
            System.err.println("[CompanionClientE2E] trace write failed: " + ignored);
        }
    }

    /** Isolated anchor type avoids relying on client mixins or injected target state. */
    private static final class EntityAnchorArgumentTypeCompat {
        static final net.minecraft.command.argument.EntityAnchorArgumentType.EntityAnchor EYES =
                net.minecraft.command.argument.EntityAnchorArgumentType.EntityAnchor.EYES;
    }
}
